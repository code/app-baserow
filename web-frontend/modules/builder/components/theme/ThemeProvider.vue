<template>
  <div :style="style" @click.self="$emit('click', $event)">
    <slot></slot>
  </div>
</template>

<script>
import { ThemeConfigBlockType } from '@baserow/modules/builder/themeConfigBlockTypes'
export default {
  name: 'ThemeProvider',
  inject: ['builder'],
  computed: {
    themeConfigBlocks() {
      return this.$registry.getOrderedList('themeConfigBlock')
    },
    style() {
      return ThemeConfigBlockType.getAllStyles(
        this.themeConfigBlocks,
        this.builder.theme
      )
    },
  },
}
</script>
