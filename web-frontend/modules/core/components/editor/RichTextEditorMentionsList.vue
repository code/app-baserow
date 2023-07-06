<template>
  <div
    class="dropdown rich-text-editor__mention-dropdown"
    :class="{
      'dropdown--floating': !showInput,
      'dropdown--disabled': disabled,
    }"
    :tabindex="realTabindex"
    @contextmenu.stop
    @focusin="show()"
    @focusout="focusout($event)"
  >
    <div class="dropdown__items" :class="{ hidden: !open }">
      <ul
        ref="items"
        v-prevent-parent-scroll
        v-auto-overflow-scroll
        class="select__items"
        tabindex=""
        @scroll="scroll"
      >
        <FieldCollaboratorDropdownItem
          v-for="collaborator in results"
          :key="collaborator.user_id"
          :name="collaborator.name"
          :value="collaborator.user_id"
        ></FieldCollaboratorDropdownItem>
      </ul>
      <div v-show="isNotFound" class="select__description">
        {{ $i18n.t('richTextEditorMentionsList.notFound') }}
      </div>
    </div>
  </div>
</template>

<script>
import inMemoryPaginatedDropdown from '@baserow/modules/core/mixins/inMemoryPaginatedDropdown'
import FieldCollaboratorDropdownItem from '@baserow/modules/database/components/field/FieldCollaboratorDropdownItem'

export default {
  name: 'RichTextEditorMentionsList',
  components: { FieldCollaboratorDropdownItem },
  mixins: [inMemoryPaginatedDropdown],
  props: {
    collaborators: {
      type: Array,
      required: true,
    },
    command: {
      type: Function,
      required: true,
    },
  },
  computed: {
    isNotFound() {
      return this.results.length === 0
    },
  },
  watch: {
    collaborators() {
      this.search()
      this.hoverFirstItem()
    },
  },
  mounted() {
    this.hoverFirstItem()
  },
  methods: {
    hoverFirstItem() {
      this.$nextTick(() => {
        this.hover = this.collaborators[0]?.user_id
      })
    },
    filterItems() {
      // No need to filter items here as collaborators are already filtered.
      return this.collaborators
    },
    onKeyDown({ event }) {
      if (event.key === 'Enter' && this.open) {
        return true // insert the selected item
      }
    },
    _select(collaborator) {
      this.command({
        id: collaborator.user_id,
        label: collaborator.name,
      })
    },
    select(collaboratorUserId) {
      const collaborator = this.collaborators.find(
        (c) => c.user_id === collaboratorUserId
      )

      if (collaborator) {
        this._select(collaborator)
      }
    },
  },
}
</script>