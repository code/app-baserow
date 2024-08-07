<template>
  <div class="image-input image-input--with-image">
    <div v-if="imageUrl" class="image-input__image-placeholder">
      <img class="image-input__image-placeholder-img" :src="imageUrl" />
    </div>
    <div class="image-input__image-upload">
      <template v-if="!hasImage">
        <p class="image-input__image-upload-description">
          {{ labelDescription || $t('imageInput.labelDescription') }}
        </p>
        <Button
          icon="iconoir-upload-square"
          type="upload"
          @click="openFileUploadModal"
        >
          {{ labelButton || $t('imageInput.labelButton') }}
        </Button>
      </template>
    </div>
    <div class="image-input__image-delete">
      <ButtonIcon
        v-if="hasImage"
        icon="iconoir-bin"
        @click="$emit('input', null)"
      />
    </div>
    <UserFilesModal
      ref="userFilesModal"
      :multiple-files="multipleFiles"
      :file-types-acceptable="allowedImageTypes"
      @uploaded="fileUploaded"
    />
  </div>
</template>

<script>
import UserFilesModal from '@baserow/modules/core/components/files/UserFilesModal'
import { UploadFileUserFileUploadType } from '@baserow/modules/core/userFileUploadTypes'
import { IMAGE_FILE_TYPES } from '@baserow/modules/core/enums'

export default {
  name: 'ImageInput',
  components: {
    UserFilesModal,
  },
  props: {
    value: {
      type: Object,
      required: false,
      default: null,
    },
    allowedImageTypes: {
      type: Array,
      required: false,
      default: () => {
        return IMAGE_FILE_TYPES
      },
    },
    multipleFiles: {
      type: Boolean,
      required: false,
      default: false,
    },
    labelDescription: {
      type: String,
      required: false,
      default: '',
    },
    labelButton: {
      type: String,
      required: false,
      default: '',
    },
    defaultImage: {
      type: String,
      required: false,
      default: null,
    },
  },
  data() {
    return {}
  },
  computed: {
    imageUrl() {
      if (this.value === null) {
        if (this.defaultImage) {
          return this.defaultImage
        } else {
          return null
        }
      }
      return this.value.url
    },
    removable() {
      return this.value !== null
    },
    hasImage() {
      return this.value !== null
    },
  },
  methods: {
    openFileUploadModal() {
      this.$refs.userFilesModal.show(UploadFileUserFileUploadType.getType())
    },
    fileUploaded([file]) {
      this.$refs.userFilesModal.hide()
      if (file?.name) {
        this.$emit('input', file)
      }
    },
  },
}
</script>
