import Vue from 'vue'
import _ from 'lodash'
import moment from '@baserow/modules/core/moment'
import { clone } from '@baserow/modules/core/utils/object'
import ViewService from '@baserow/modules/database/services/view'
import CalendarService from '@baserow_premium/services/views/calendar'
import {
  getRowSortFunction,
  matchSearchFilters,
} from '@baserow/modules/database/utils/view'
import RowService from '@baserow/modules/database/services/row'
import {
  getMonthlyTimestamps,
  getUserTimeZone,
} from '@baserow/modules/core/utils/date'

export function populateRow(row) {
  row._ = {}
  return row
}

export function populateDateStack(stack) {
  Object.assign(stack, {
    loading: false,
  })
  stack.results.forEach((row) => {
    populateRow(row)
  })
  return stack
}

export const state = () => ({
  loading: false,
  // The calendar view id that is being displayed
  lastCalendarId: null,
  // The chosen date field that the
  // items will be organized by in the view
  dateFieldId: null,
  fieldOptions: {},
  // dateStack organizes rows by dates (2023-02-21)
  // based on the date field with dateFieldId
  dateStacks: {},
  // How many items per date are fetched
  bufferRequestSize: 10,
  // Determines currently selected time period
  // based on a specific date. For example, if selectedDate
  // is today, the calendar view will be showing the
  // current month surrounding it.
  // It is an instance of moment.
  selectedDate: null,
})

export const mutations = {
  RESET(state, getters) {
    state.loadingRows = false
    state.lastCalendarId = null
    state.dateFieldId = null
    state.fieldOptions = {}
    state.dateStacks = {}
  },
  SET_LOADING_ROWS(state, loading) {
    state.loadingRows = loading
  },
  SET_LAST_CALENDAR_ID(state, calendarId) {
    state.lastCalendarId = calendarId
  },
  SET_DATE_FIELD_ID(state, dateFieldId) {
    state.dateFieldId = dateFieldId
  },
  SET_SELECTED_DATE(state, selectedDate) {
    // Store as a unix timestamp so the serialization from Nuxt -> Client works as
    // you can't safely serialize and transmit an entire moment object.
    state.selectedDate = selectedDate.valueOf()
  },
  REPLACE_ALL_DATE_STACKS(state, stacks) {
    state.dateStacks = stacks
  },
  ADD_ROWS_TO_STACK(state, { date, count, rows }) {
    if (count) {
      state.dateStacks[date].count = count
    }
    state.dateStacks[date].results.push(...rows)
  },
  ADD_STACK(state, { date, stack }) {
    Vue.set(state.dateStacks, date, stack)
  },
  REPLACE_ALL_FIELD_OPTIONS(state, fieldOptions) {
    state.fieldOptions = fieldOptions
  },
  UPDATE_ALL_FIELD_OPTIONS(state, fieldOptions) {
    state.fieldOptions = _.merge({}, state.fieldOptions, fieldOptions)
  },
  UPDATE_FIELD_OPTIONS_OF_FIELD(state, { fieldId, values }) {
    if (Object.prototype.hasOwnProperty.call(state.fieldOptions, fieldId)) {
      Object.assign(state.fieldOptions[fieldId], values)
    } else {
      state.fieldOptions = Object.assign({}, state.fieldOptions, {
        [fieldId]: values,
      })
    }
  },
  DELETE_FIELD_OPTIONS(state, fieldId) {
    if (Object.prototype.hasOwnProperty.call(state.fieldOptions, fieldId)) {
      delete state.fieldOptions[fieldId]
    }
  },
  ADD_FIELD_TO_ALL_ROWS(state, { field, value }) {
    const name = `field_${field.id}`
    Object.keys(state.dateStacks).forEach((stack) => {
      // We have to replace all the rows by using the map function to make it
      // reactive and update immediately.
      state.dateStacks[stack].results = state.dateStacks[stack].results.map(
        (row) => {
          if (
            row !== null &&
            !Object.prototype.hasOwnProperty.call(row, name)
          ) {
            row[`field_${field.id}`] = value
            return { ...row }
          }
          return row
        }
      )
    })
  },
  CREATE_ROW(state, { row, stackId, index }) {
    state.dateStacks[stackId].results.splice(index, 0, row)
  },
  UPDATE_ROW(state, { row, values }) {
    Object.keys(state.dateStacks).forEach((stack) => {
      const rows = state.dateStacks[stack].results
      const index = rows.findIndex((item) => item.id === row.id)
      if (index !== -1) {
        const existingRowState = rows[index]
        Object.assign(existingRowState, values)
      }
    })
  },
  UPDATE_VALUE_OF_ALL_ROWS_IN_STACK(state, { fieldId, stackId, values }) {
    const name = `field_${fieldId}`
    state.dateStacks[stackId].results.forEach((row) => {
      Object.assign(row[name], values)
    })
  },
  MOVE_ROW(
    state,
    { currentStackId, currentIndex, targetStackId, targetIndex }
  ) {
    state.dateStacks[targetStackId].results.splice(
      targetIndex,
      0,
      state.dateStacks[currentStackId].results.splice(currentIndex, 1)[0]
    )
  },
  DELETE_ROW(state, { stackId, index }) {
    state.dateStacks[stackId].results.splice(index, 1)
  },
  INCREASE_COUNT(state, { stackId }) {
    state.dateStacks[stackId].count++
  },
  DECREASE_COUNT(state, { stackId }) {
    state.dateStacks[stackId].count--
  },
}

export const actions = {
  /**
   * Resets the store completely throwing away all state.
   */
  reset({ dispatch, commit, getters }, _) {
    commit('RESET')
  },
  /**
   * Resets the store completely throwing away all state and loads new rows given
   * a new view etc.
   * rows.
   */
  async resetAndFetchInitial(
    { dispatch, commit, getters },
    { calendarId, dateFieldId, fields, includeFieldOptions = true }
  ) {
    commit('RESET')
    await dispatch('refreshAndFetchInitial', {
      calendarId,
      dateFieldId,
      fields,
      includeFieldOptions,
    })
  },
  /**
   * Refreshes the store given new date and view parameters and then refetches the
   * rows. Doesn't throw away field options etc.
   */
  async refreshAndFetchInitial(
    { dispatch, commit, getters },
    { calendarId, dateFieldId, fields, includeFieldOptions = true }
  ) {
    commit('SET_DATE_FIELD_ID', dateFieldId)
    commit('SET_LAST_CALENDAR_ID', calendarId)
    await dispatch('fetchInitial', {
      includeFieldOptions,
      fields,
    })
  },
  /**
   * Fetches an initial set of rows and adds that data to the store.
   */
  async fetchInitial(
    { dispatch, commit, getters },
    { fields, includeFieldOptions = true }
  ) {
    // We can't guess the users timezone when doing the server side render.
    // So we only can know what today is and load rows in the client side when the
    // field does not have a forced timezone.
    if (!process.server || getters.getFieldTimeZoneIfSet(fields)) {
      const timezone = getters.getTimeZone(fields)
      const todayOrSelectedDay =
        getters.getSelectedDate(fields) == null
          ? moment.tz(timezone)
          : getters.getSelectedDate(fields)
      await dispatch('fetchMonthly', {
        dateTime: todayOrSelectedDay,
        fields,
        includeFieldOptions,
      })
    }
  },
  /**
   * Fetches a set of rows based on the provided datetime.
   */
  async fetchMonthly(
    { commit, getters },
    { dateTime, fields, includeFieldOptions = false }
  ) {
    commit('SET_SELECTED_DATE', dateTime)

    const df = getters.getDateField(fields)
    if (
      !df ||
      this.$registry.get('field', df.type).canRepresentDate() === false
    ) {
      commit('RESET')
      return
    }

    commit('SET_LOADING_ROWS', true)
    const { fromTimestamp, toTimestamp } = getMonthlyTimestamps(dateTime)
    try {
      const { data } = await CalendarService(this.$client).fetchRows({
        calendarId: getters.getLastCalendarId,
        limit: getters.getBufferRequestSize,
        offset: 0,
        includeFieldOptions,
        fromTimestamp,
        toTimestamp,
        userTimeZone: getUserTimeZone(),
      })
      const lastRequest = dateTime.isSame(getters.getSelectedDate(fields))
      if (lastRequest) {
        Object.keys(data.rows).forEach((key) => {
          populateDateStack(data.rows[key])
        })
        commit('REPLACE_ALL_DATE_STACKS', data.rows)
        if (includeFieldOptions) {
          commit('REPLACE_ALL_FIELD_OPTIONS', data.field_options)
        }
        commit('SET_LOADING_ROWS', false)
      }
    } catch (error) {
      if (error.handler.code === 'ERROR_CALENDAR_VIEW_HAS_NO_DATE_FIELD') {
        commit('RESET')
      } else {
        throw error
      }
    } finally {
      const lastRequest = dateTime.isSame(getters.getSelectedDate(fields))
      if (lastRequest) {
        commit('SET_LOADING_ROWS', false)
      }
    }
  },
  /**
   * This action is called when the users scrolls to the end of the stack. Because
   * we don't fetch all the rows, the next set will be fetched when the user reaches
   * the end.
   */
  async fetchMore(
    { dispatch, commit, getters, rootGetters },
    { date, fields }
  ) {
    const stack = getters.getDateStack(date)
    const rows = stack.results
    const timezone = getters.getTimeZone(fields)
    const fromTimestamp = moment.tz(date, timezone)
    const toTimestamp = moment.tz(fromTimestamp, timezone).add(1, 'day')
    const { data } = await CalendarService(this.$client).fetchRows({
      calendarId: getters.getLastCalendarId,
      limit: getters.getBufferRequestSize,
      offset: rows.length,
      includeFieldOptions: false,
      fromTimestamp,
      toTimestamp,
      userTimeZone: getUserTimeZone(),
    })
    const newRows = data.rows[date].results
    const newCount = data.rows[date].count
    newRows.forEach((row) => {
      populateRow(row)
    })
    commit('ADD_ROWS_TO_STACK', { date, count: newCount, rows: newRows })
  },
  /**
   * Updates the field options of a given field in the store. So no API request to
   * the backend is made.
   */
  setFieldOptionsOfField({ commit }, { field, values }) {
    commit('UPDATE_FIELD_OPTIONS_OF_FIELD', {
      fieldId: field.id,
      values,
    })
  },
  /**
   * Replaces all field options with new values and also makes an API request to the
   * backend with the changed values. If the request fails the action is reverted.
   */
  async updateAllFieldOptions(
    { dispatch, getters, rootGetters },
    { newFieldOptions, oldFieldOptions, readOnly = false }
  ) {
    dispatch('forceUpdateAllFieldOptions', newFieldOptions)

    const calendarId = getters.getLastCalendarId
    if (!readOnly) {
      const updateValues = { field_options: newFieldOptions }

      try {
        await ViewService(this.$client).updateFieldOptions({
          viewId: calendarId,
          values: updateValues,
        })
      } catch (error) {
        dispatch('forceUpdateAllFieldOptions', oldFieldOptions)
        throw error
      }
    }
  },
  /**
   * Forcefully updates all field options without making a call to the backend.
   */
  forceUpdateAllFieldOptions({ commit }, fieldOptions) {
    commit('UPDATE_ALL_FIELD_OPTIONS', fieldOptions)
  },
  /**
   * Deletes the field options of the provided field id if they exist.
   */
  forceDeleteFieldOptions({ commit }, fieldId) {
    commit('DELETE_FIELD_OPTIONS', fieldId)
  },
  /**
   * Updates the order of all the available field options. The provided order parameter
   * should be an array containing the field ids in the correct order.
   */
  async updateFieldOptionsOrder(
    { commit, getters, dispatch },
    { order, readOnly = false }
  ) {
    const oldFieldOptions = clone(getters.getAllFieldOptions)
    const newFieldOptions = clone(getters.getAllFieldOptions)

    // Update the order of the field options that have not been provided in the order.
    // They will get a position that places them after the provided field ids.
    let i = 0
    Object.keys(newFieldOptions).forEach((fieldId) => {
      if (!order.includes(parseInt(fieldId))) {
        newFieldOptions[fieldId].order = order.length + i
        i++
      }
    })

    // Update create the field options and set the correct order value.
    order.forEach((fieldId, index) => {
      const id = fieldId.toString()
      if (Object.prototype.hasOwnProperty.call(newFieldOptions, id)) {
        newFieldOptions[fieldId.toString()].order = index
      }
    })

    return await dispatch('updateAllFieldOptions', {
      oldFieldOptions,
      newFieldOptions,
      readOnly,
    })
  },
  /**
   * Updates the field options of a specific field.
   */
  async updateFieldOptionsOfField(
    { commit, getters, rootGetters },
    { view, field, values, readOnly = false }
  ) {
    commit('UPDATE_FIELD_OPTIONS_OF_FIELD', {
      fieldId: field.id,
      values,
    })

    if (!readOnly) {
      const calendarId = getters.getLastCalendarId
      const oldValues = clone(getters.getAllFieldOptions[field.id])
      const updateValues = { field_options: {} }
      updateValues.field_options[field.id] = values

      try {
        await ViewService(this.$client).updateFieldOptions({
          viewId: calendarId,
          values: updateValues,
        })
      } catch (error) {
        commit('UPDATE_FIELD_OPTIONS_OF_FIELD', {
          fieldId: field.id,
          values: oldValues,
        })
        throw error
      }
    }
  },
  /**
   * Can be called when a new row has been created. This action will make sure that
   * the state is updated accordingly. If the newly created position is within the
   * current buffer (`dateStack.results`), then it will be added there, otherwise, just
   * the count is increased.
   *
   * @param values  The values of the newly created row.
   * @param row     Can be provided when the row already existed within the state.
   *                In that case, the `_` data will be preserved. Can be useful when
   *                a row has been updated while being dragged.
   */
  async createdNewRow(
    { dispatch, commit, getters, rootGetters },
    { view, values, fields }
  ) {
    const row = clone(values)
    populateRow(row)

    const matchesFilters = await dispatch('rowMatchesFilters', {
      view,
      row,
      fields,
    })
    if (!matchesFilters) {
      return
    }

    const dateFieldId = getters.getDateFieldIdIfNotTrashed(fields)
    const value = row[`field_${dateFieldId}`]
    const timezone = getters.getTimeZone(fields)
    const stackId = moment.tz(value, timezone).format('YYYY-MM-DD')
    const stack = getters.getDateStack(stackId)
    if (stack === undefined) {
      return
    }
    const sortings = [{ field: dateFieldId, value: 'ASC', order: 'ASC' }]
    const sortedRows = clone(stack.results)
    sortedRows.push(row)
    sortedRows.sort(getRowSortFunction(this.$registry, sortings, fields))
    const index = sortedRows.findIndex((r) => r.id === row.id)
    const isLast = index === sortedRows.length - 1

    // Because we don't fetch all the rows from the backend, we can't know for sure
    // whether or not the row is being added at the right position. Therefore, if
    // it's last, we just not add it to the store and wait for the user to fetch the
    // next page.
    if (!isLast || stack.results.length === stack.count) {
      commit('CREATE_ROW', { row, stackId, index })
    }
    // We always need to increase the count whether row has been added to the store
    // or not because the count is for all the rows and not just the ones in the store.
    commit('INCREASE_COUNT', { stackId })
  },
  /**
   * Can be called when a row in the table has been deleted. This action will make
   * sure that the state is updated accordingly.
   */
  async deletedExistingRow(
    { dispatch, commit, getters },
    { view, row, fields }
  ) {
    row = clone(row)
    populateRow(row)

    const matchesFilters = await dispatch('rowMatchesFilters', {
      view,
      row,
      fields,
    })
    if (!matchesFilters) {
      return
    }

    const dateFieldId = getters.getDateFieldIdIfNotTrashed(fields)
    const value = row[`field_${dateFieldId}`]
    const timezone = getters.getTimeZone(fields)
    const stackId = value
      ? moment.tz(value, timezone).format('YYYY-MM-DD')
      : null
    const stack = getters.getDateStack(stackId)
    const current = getters.findStackIdAndIndex(row.id)
    if (current !== undefined) {
      const currentStackId = current[0]
      const currentIndex = current[1]
      const currentRow = current[2]
      commit('DELETE_ROW', { stackId: currentStackId, index: currentIndex })
      commit('DECREASE_COUNT', { stackId: currentStackId })
      return currentRow
    } else if (stack) {
      commit('DECREASE_COUNT', { stackId })
    }

    return null
  },
  /**
   * Can be called when a row in the table has been updated. This action will make sure
   * that the state is updated accordingly. If the date field value has
   * changed, the row will be moved to the right stack. If the position has changed,
   * it will be moved to the right position.
   */
  async updatedExistingRow(
    { dispatch, getters, commit },
    { view, row, values, fields }
  ) {
    const dateFieldId = getters.getDateFieldIdIfNotTrashed(fields)
    const fieldName = `field_${dateFieldId}`

    // First, we virtually need to figure out if the row was in the old stack.
    const oldRow = populateRow(clone(row))
    const oldRowMatchesFilters = await dispatch('rowMatchesFilters', {
      view,
      row: oldRow,
      fields,
    })
    const oldValue = oldRow[fieldName]
    const timezone = getters.getTimeZone(fields)
    const oldStackId = moment.tz(oldValue, timezone).format('YYYY-MM-DD')
    const oldStack = getters.getDateStack(oldStackId)
    let oldExists = false
    let oldExistingIndex = -1
    if (oldStack) {
      const oldStackResults = clone(oldStack.results)
      oldExistingIndex = oldStackResults.findIndex((r) => r.id === oldRow.id)
      oldExists = oldExistingIndex > -1 && oldRowMatchesFilters
    }

    // Second, we need to figure out if the row should be visible in the new stack.
    const newRow = Object.assign(populateRow(clone(row)), values)
    const newRowMatchesFilters = await dispatch('rowMatchesFilters', {
      view,
      row: newRow,
      fields,
    })
    const newValue = newRow[fieldName]
    const newStackId = moment.tz(newValue, timezone).format('YYYY-MM-DD')
    const newStack = getters.getDateStack(newStackId)
    let newExists = false
    let newIndex = -1
    if (newStack) {
      const newStackResults = newStack ? clone(newStack.results) : []
      const newRowCurrentIndex = newStackResults.findIndex(
        (r) => r.id === newRow.id
      )
      let newStackCount = newStack.count
      if (newRowCurrentIndex > -1) {
        newStackResults.splice(newRowCurrentIndex, 1)
        newStackCount--
      }
      newStackResults.push(newRow)
      newStackCount++
      const sortings = [{ field: dateFieldId, value: 'ASC', order: 'ASC' }]
      newStackResults.sort(getRowSortFunction(this.$registry, sortings, fields))
      newIndex = newStackResults.findIndex((r) => r.id === newRow.id)
      const newIsLast = newIndex === newStackResults.length - 1
      newExists =
        (!newIsLast || newStackResults.length === newStackCount) &&
        newRowMatchesFilters
    }

    commit('UPDATE_ROW', { row, values })

    if (oldExists && newExists) {
      commit('MOVE_ROW', {
        currentStackId: oldStackId,
        currentIndex: oldExistingIndex,
        targetStackId: newStackId,
        targetIndex: newIndex,
      })
      commit('DECREASE_COUNT', { stackId: oldStackId })
      commit('INCREASE_COUNT', { stackId: newStackId })
    } else if (oldExists && !newExists) {
      commit('DELETE_ROW', { stackId: oldStackId, index: oldExistingIndex })
      commit('DECREASE_COUNT', { stackId: oldStackId })
    } else if (!oldExists && newExists) {
      commit('CREATE_ROW', {
        row: newRow,
        stackId: newStackId,
        index: newIndex,
      })
      commit('INCREASE_COUNT', { stackId: newStackId })
    }
  },
  /**
   * Check if the provided row matches the provided view filters.
   */
  rowMatchesFilters(context, { view, fields, row, overrides = {} }) {
    const values = JSON.parse(JSON.stringify(row))
    Object.assign(values, overrides)

    // The value is always valid if the filters are disabled.
    return view.filters_disabled
      ? true
      : matchSearchFilters(
          this.$registry,
          view.filter_type,
          view.filters,
          fields,
          values
        )
  },
  /**
   * Updates the value of a row and make the changes to the store accordingly.
   */
  async updateRowValue(
    { commit, dispatch },
    { view, table, row, field, fields, value, oldValue }
  ) {
    const fieldType = this.$registry.get('field', field._.type.type)
    const newValues = {}
    const newValuesForUpdate = {}
    const oldValues = {}
    const fieldName = `field_${field.id}`
    newValues[fieldName] = value
    newValuesForUpdate[fieldName] = fieldType.prepareValueForUpdate(
      field,
      value
    )
    oldValues[fieldName] = oldValue

    fields.forEach((fieldToCall) => {
      const fieldType = this.$registry.get('field', fieldToCall._.type.type)
      const fieldToCallName = `field_${fieldToCall.id}`
      const currentFieldValue = row[fieldToCallName]
      const optimisticFieldValue = fieldType.onRowChange(
        row,
        fieldToCall,
        currentFieldValue
      )

      if (currentFieldValue !== optimisticFieldValue) {
        newValues[fieldToCallName] = optimisticFieldValue
        oldValues[fieldToCallName] = currentFieldValue
      }
    })

    await dispatch('updatedExistingRow', {
      view,
      row,
      values: newValues,
      fields,
    })

    try {
      const { data } = await RowService(this.$client).update(
        table.id,
        row.id,
        newValuesForUpdate
      )
      commit('UPDATE_ROW', { row, values: data })
    } catch (error) {
      await dispatch('updatedExistingRow', {
        view,
        row,
        values: oldValues,
        fields,
      })
      throw error
    }
  },
  /**
   * Adds a field with a provided value to the rows in the store. This will for
   * example be called when a new field has been created.
   */
  addField({ commit }, { field, value = null }) {
    commit('ADD_FIELD_TO_ALL_ROWS', { field, value })
  },
  selectDateAndStartLoading({ commit }, { selectedDate }) {
    commit('SET_LOADING_ROWS', true)
    commit('SET_SELECTED_DATE', selectedDate)
  },
}

export const getters = {
  getLoadingRows(state) {
    return state.loadingRows
  },
  getLastCalendarId(state) {
    return state.lastCalendarId
  },
  getDateFieldIdIfNotTrashed: (state, getters) => (fields) => {
    return getters.getDateField(fields)?.id
  },
  getAllFieldOptions(state) {
    return state.fieldOptions
  },
  getDateStack: (state) => (date) => {
    return state.dateStacks[date]
  },
  getBufferRequestSize(state) {
    return state.bufferRequestSize
  },
  getSelectedDate: (state, getters) => (fields) => {
    return state.selectedDate
      ? moment(state.selectedDate).tz(getters.getTimeZone(fields))
      : null
  },
  getAllRows(state) {
    let rows = []
    Object.keys(state.dateStacks).forEach((key) => {
      rows = rows.concat(state.dateStacks[key].results)
    })
    return rows
  },
  findStackIdAndIndex: (state) => (rowId) => {
    const stacks = state.dateStacks
    const keys = Object.keys(stacks)
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i]
      const results = stacks[key].results
      for (let i2 = 0; i2 < results.length; i2++) {
        const result = results[i2]
        if (result.id === rowId) {
          return [key, i2, result]
        }
      }
    }
  },
  getDateField: (state) => (fields) => {
    const fieldId = state.dateFieldId
    if (fieldId) {
      return fields.find((field) => field.id === fieldId)
    } else {
      return null
    }
  },
  getFieldTimeZoneIfSet: (state, getters) => (fields) => {
    const dateField = getters.getDateField(fields)
    if (dateField?.date_include_time) {
      return dateField?.date_force_timezone
    } else {
      return 'UTC'
    }
  },
  getTimeZone: (state, getters) => (fields) => {
    const fieldTimezone = getters.getFieldTimeZoneIfSet(fields)
    return fieldTimezone || getUserTimeZone()
  },
  getCalendarTimezoneAndDateLoaded: (state, getters) => (fields) => {
    return getters.getSelectedDate(fields) != null
  },
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
