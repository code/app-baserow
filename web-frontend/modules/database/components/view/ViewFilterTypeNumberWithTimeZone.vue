<template>
  <div class="filters__multi-value">
    <FormInput
      ref="input"
      v-model="xAgo"
      type="text"
      :error="$v.xAgo.$error"
      :disabled="disabled"
      @input=";[setCopy($event), delayedUpdate($event, true)]"
      @keydown.enter=";[setCopy($event), delayedUpdate($event, true)]"
    ></FormInput>

    <span class="filters__value-timezone">{{ getTimezoneAbbr() }}</span>
  </div>
</template>

<script>
import { integer, required } from 'vuelidate/lib/validators'
import filterTypeDateInput from '@baserow/modules/database/mixins/filterTypeDateInput'

export default {
  name: 'ViewFilterTypeNumberWithTimeZone',
  mixins: [filterTypeDateInput],
  data() {
    return {
      xAgo: '',
    }
  },
  methods: {
    isInputValid() {
      return !this.$v.xAgo.$error
    },
    setCopy(value, sender) {
      const [, xAgo] = this.splitCombinedValue(value)
      this.xAgo = xAgo
    },
  },
  validations: {
    copy: { required },
    xAgo: { integer },
  },
}
</script>
