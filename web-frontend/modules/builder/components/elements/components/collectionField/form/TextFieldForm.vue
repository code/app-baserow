<template>
  <form @submit.prevent @keydown.enter.prevent>
    <ApplicationBuilderFormulaInputGroup
      v-model="values.value"
      small
      :label="$t('textFieldForm.fieldValueLabel')"
      :placeholder="$t('textFieldForm.fieldValuePlaceholder')"
      :data-providers-allowed="DATA_PROVIDERS_ALLOWED_ELEMENTS"
      horizontal
      small-label
    />
  </form>
</template>

<script>
import collectionFieldForm from '@baserow/modules/builder/mixins/collectionFieldForm'
import ApplicationBuilderFormulaInputGroup from '@baserow/modules/builder/components/ApplicationBuilderFormulaInputGroup'

export default {
  name: 'TextField',
  components: { ApplicationBuilderFormulaInputGroup },
  mixins: [collectionFieldForm],
  data() {
    return {
      allowedValues: ['value'],
      values: {
        value: '',
      },
    }
  },
}
</script>
