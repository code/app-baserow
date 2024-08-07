<template>
  <div class="field-date__container">
    <FormGroup class="field-date" :error="touched && !valid">
      <FormInput
        ref="date"
        v-model="date"
        size="large"
        :error="touched && !valid"
        :placeholder="getDatePlaceholder(field)"
        :disabled="readOnly"
        icon-right="iconoir-calendar"
        @keyup.enter="$refs.date.blur()"
        @keyup="updateDate(field, date)"
        @focus="focus($refs.dateContext, $event)"
        @blur="blur($refs.dateContext, $event)"
      ></FormInput>

      <Context
        ref="dateContext"
        :hide-on-click-outside="false"
        class="datepicker-context"
      >
        <client-only>
          <date-picker
            v-if="!readOnly"
            :inline="true"
            :monday-first="true"
            :use-utc="true"
            :value="pickerDate"
            :language="datePickerLang[$i18n.locale]"
            class="datepicker"
            @input="chooseDate(field, $event)"
          ></date-picker>
        </client-only>
      </Context>
    </FormGroup>

    <FormGroup
      v-if="field.date_include_time"
      :error="touched && !valid"
      class="field-date__time"
    >
      <FormInput
        ref="time"
        v-model="time"
        size="large"
        :error="touched && !valid"
        :placeholder="getTimePlaceholder(field)"
        :disabled="readOnly"
        icon-right="iconoir-clock"
        @keyup.enter="$refs.time.blur()"
        @keyup="updateTime(field, time)"
        @focus="focus($refs.timeContext, $event)"
        @blur="blur($refs.timeContext, $event)"
      />

      <TimeSelectContext
        v-if="!readOnly"
        ref="timeContext"
        :value="time"
        :hide-on-click-outside="false"
        :notation="field.date_time_format"
        @input="chooseTime(field, $event)"
      ></TimeSelectContext>

      <template #error>
        <span v-show="touched && !valid">
          {{ error }}
        </span>
      </template>
    </FormGroup>

    <div class="field-date__tzinfo">
      {{ getCellTimezoneAbbr(field, value, { force: true }) }}
    </div>
  </div>
</template>
<script>
import TimeSelectContext from '@baserow/modules/core/components/TimeSelectContext'
import rowEditField from '@baserow/modules/database/mixins/rowEditField'
import rowEditFieldInput from '@baserow/modules/database/mixins/rowEditFieldInput'
import dateField from '@baserow/modules/database/mixins/dateField'
import { en, fr } from 'vuejs-datepicker/dist/locale'

export default {
  components: { TimeSelectContext },
  mixins: [rowEditField, rowEditFieldInput, dateField],
  data() {
    return {
      datePickerLang: {
        en,
        fr,
      },
    }
  },
  methods: {
    focus(...args) {
      this.select()
      dateField.methods.focus.call(this, ...args)
    },
    blur(...args) {
      dateField.methods.blur.call(this, ...args)
      this.unselect()
    },
  },
}
</script>
