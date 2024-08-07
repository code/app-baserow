<template>
  <Modal @show="onShow()">
    <h2 class="box__title">
      {{ $t('publishActionModal.title') }}
    </h2>
    <Error :error="error"></Error>

    <template v-if="!hasVisibleError">
      <template v-if="domains.length">
        <p>{{ $t('publishActionModal.description') }}</p>

        <div
          v-for="(domain, index) in domains"
          :key="domain.id"
          class="publish-action-modal__container"
        >
          <Radio v-model="selectedDomain" :value="domain.id">
            <span class="publish-action-modal__domain-name">{{
              domain.domain_name
            }}</span>
            <a
              v-tooltip="$t('action.copyToClipboard')"
              class="publish-action-modal__copy-domain"
              tooltip-position="top"
              @click.stop="
                ;[copyDomainUrl(domain), $refs.domainCopied[index].show()]
              "
            >
              <i class="iconoir-copy" />
              <Copied ref="domainCopied" />
            </a>
            <a
              v-tooltip="$t('publishActionModal.openInNewTab')"
              tooltip-position="top"
              class="publish-action-modal__domain-link"
              :href="getDomainUrl(domain)"
              target="_blank"
              @click.stop=""
            >
              <i class="iconoir-open-new-window" />
            </a>
          </Radio>
          <LastPublishedDomainDate
            :domain="domain"
            class="publish-action-modal__last-update"
          />
        </div>
      </template>
      <p v-else>{{ $t('publishActionModal.noDomain') }}</p>
    </template>

    <Alert v-if="jobHasSucceeded" type="success">
      <template #title>{{
        $t('publishActionModal.publishSucceedTitle')
      }}</template>
      <p>{{ $t('publishActionModal.publishSucceedDescription') }}</p>
    </Alert>

    <div class="modal-progress__actions">
      <ProgressBar
        v-if="jobIsRunning"
        :value="job.progress_percentage"
        :status="jobHumanReadableState"
      />
      <div class="align-right">
        <Button
          size="large"
          :loading="jobIsRunning || loading"
          :disabled="loading || jobIsRunning || !selectedDomain"
          @click="publishSite()"
        >
          {{ $t('publishActionModal.publish') }}
        </Button>
      </div>
    </div>
  </Modal>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import modal from '@baserow/modules/core/mixins/modal'
import error from '@baserow/modules/core/mixins/error'
import jobProgress from '@baserow/modules/core/mixins/jobProgress'
import PublishedDomainService from '@baserow/modules/builder/services/publishedBuilder'
import { notifyIf } from '@baserow/modules/core/utils/error'
import { copyToClipboard } from '@baserow/modules/database/utils/clipboard'
import LastPublishedDomainDate from '@baserow/modules/builder/components/domain/LastPublishedDomainDate'

export default {
  name: 'PublishActionModal',
  components: { LastPublishedDomainDate },
  mixins: [modal, error, jobProgress],
  props: {
    builder: {
      type: Object,
      required: true,
    },
  },
  data() {
    return { selectedDomain: null, loading: false }
  },
  computed: {
    ...mapGetters({ domains: 'domain/getDomains' }),
  },
  watch: {
    selectedDomain() {
      this.job = null
    },
  },
  beforeDestroy() {
    this.stopPollIfRunning()
  },
  methods: {
    ...mapActions({
      actionFetchDomains: 'domain/fetch',
      actionForceUpdateDomain: 'domain/forceUpdate',
    }),
    async onShow() {
      this.hideError()
      this.job = null
      this.loading = false
      this.selectedDomain = null
      try {
        await this.actionFetchDomains({ builderId: this.builder.id })
        this.hideError()
      } catch (error) {
        this.handleError(error)
      }
    },
    async publishSite() {
      this.loading = true
      this.hideError()
      const { data: job } = await PublishedDomainService(this.$client).publish({
        id: this.selectedDomain,
      })

      this.startJobPoller(job)
    },
    onJobFailed() {
      this.showError(
        this.$t('publishActionModal.publishFailedTitle'),
        this.$t('publishActionModal.publishFailedDescription')
      )
      this.loading = false
    },
    onJobDone() {
      this.actionForceUpdateDomain({
        domainId: this.selectedDomain,
        values: { last_published: new Date() },
      })
      this.loading = false
    },
    onJobPollingError(error) {
      notifyIf(error)
      this.loading = false
    },
    getDomainUrl(domain) {
      const url = new URL(this.$config.PUBLIC_WEB_FRONTEND_URL)
      return `${url.protocol}//${domain.domain_name}${
        url.port ? `:${url.port}` : ''
      }`
    },
    copyDomainUrl(domain) {
      copyToClipboard(this.getDomainUrl(domain))
    },
    getCustomHumanReadableJobState(state) {
      if (state === 'importing') {
        return this.$t('publishActionModal.importingState')
      }
      return ''
    },
  },
}
</script>
