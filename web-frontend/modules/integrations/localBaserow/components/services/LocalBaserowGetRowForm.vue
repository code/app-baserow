<template>
  <form @submit.prevent>
    <div>
      <div class="row">
        <div class="col col-12">
          <LocalBaserowTableSelector
            v-model="fakeTableId"
            class="local-baserow-get-row-form__table-selector"
            :databases="databases"
            :view-id.sync="values.view_id"
          ></LocalBaserowTableSelector>
        </div>
      </div>
      <div class="row">
        <div class="col col-6">
          <InjectedFormulaInputGroup
            v-model="values.row_id"
            small
            :label="$t('localBaserowGetRowForm.rowFieldLabel')"
            :placeholder="$t('localBaserowGetRowForm.rowFieldPlaceHolder')"
            :help-text="$t('localBaserowGetRowForm.rowFieldHelpText')"
          />
        </div>
      </div>
      <div class="row">
        <div class="col col-12">
          <Tabs>
            <Tab
              :title="$t('localBaserowGetRowForm.filterTabTitle')"
              class="data-source-form__condition-form-tab"
            >
              <LocalBaserowTableServiceConditionalForm
                v-if="values.table_id && dataSource.schema"
                v-model="dataSourceFilters"
                :schema="dataSource.schema"
                :table-loading="tableLoading"
                :filter-type.sync="values.filter_type"
              >
              </LocalBaserowTableServiceConditionalForm>
              <p v-if="!values.table_id">
                {{ $t('localBaserowGetRowForm.noTableChosenForFiltering') }}
              </p>
            </Tab>
            <Tab
              :title="$t('localBaserowGetRowForm.searchTabTitle')"
              class="data-source-form__condition-search-tab"
            >
              <InjectedFormulaInputGroup
                v-model="values.search_query"
                small
                :placeholder="
                  $t('localBaserowGetRowForm.searchFieldPlaceHolder')
                "
              />
            </Tab>
          </Tabs>
        </div>
      </div>
    </div>
  </form>
</template>

<script>
import form from '@baserow/modules/core/mixins/form'
import { DATA_PROVIDERS_ALLOWED_DATA_SOURCES } from '@baserow/modules/builder/enums'
import LocalBaserowTableSelector from '@baserow/modules/integrations/localBaserow/components/services/LocalBaserowTableSelector'
import LocalBaserowTableServiceConditionalForm from '@baserow/modules/integrations/localBaserow/components/services/LocalBaserowTableServiceConditionalForm'
import InjectedFormulaInputGroup from '@baserow/modules/core/components/formula/InjectedFormulaInputGroup'

export default {
  components: {
    InjectedFormulaInputGroup,
    LocalBaserowTableSelector,
    LocalBaserowTableServiceConditionalForm,
  },
  mixins: [form],
  inject: ['page'],
  provide() {
    return { dataProvidersAllowed: DATA_PROVIDERS_ALLOWED_DATA_SOURCES }
  },
  props: {
    builder: {
      type: Object,
      required: true,
    },
    contextData: {
      type: Object,
      required: false,
      default: () => ({
        databases: [],
      }),
    },
    dataSource: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      allowedValues: [
        'table_id',
        'view_id',
        'row_id',
        'search_query',
        'filters',
        'filter_type',
      ],
      values: {
        table_id: null,
        view_id: null,
        row_id: '',
        search_query: '',
        filters: [],
        filter_type: 'AND',
      },
      tableLoading: false,
    }
  },
  computed: {
    dataSourceFilters: {
      get() {
        return this.excludeTrashedFields(this.values.filters)
      },
      set(newValue) {
        this.values.filters = newValue
      },
    },
    dataSourceLoading() {
      return this.$store.getters['dataSource/getLoading'](this.page)
    },
    fakeTableId: {
      get() {
        return this.values.table_id
      },
      set(newValue) {
        // If we currently have a `table_id` selected, and the `newValue`
        // is different to the current `table_id`, then reset the `filters`
        // to a blank array, and `view_id` to `null`.
        if (this.values.table_id && this.values.table_id !== newValue) {
          this.values.filters = []
          this.values.view_id = null
        }
        this.values.table_id = newValue
      },
    },
    databases() {
      return this.contextData?.databases || []
    },
  },
  watch: {
    'values.table_id'(newValue, oldValue) {
      if (oldValue && newValue !== oldValue) {
        this.tableLoading = true
      }
    },
    dataSourceLoading: {
      handler() {
        this.tableLoading = false
      },
      immediate: true,
    },
  },
  methods: {
    /**
     * Given an array of objects containing a `field` property (e.g. the data
     * source filters array), this method will return a new array
     * containing only the objects where the field is part of the schema, so,
     * untrashed.
     *
     * @param {Array} value - The array of objects to filter.
     * @returns {Array} - The filtered array.
     */
    excludeTrashedFields(value) {
      const schema = this.dataSource.schema
      const schemaProperties =
        schema.type === 'array' ? schema.items.properties : schema.properties
      const localBaserowFieldIds = Object.values(schemaProperties)
        .filter(({ metadata }) => metadata)
        .map((prop) => prop.metadata.id)
      return value.filter(({ field }) => localBaserowFieldIds.includes(field))
    },
  },
}
</script>
