import { Registerable } from '@baserow/modules/core/registry'

/**
 */
export class PermissionManagerType extends Registerable {
  /**
   * This method will be called by the `$hasPermission` plugin for each entry of the
   * loaded permission object. This method should return `true` if the permission is
   * granted, `false` if it is disallowed and `null` if the permission manager doesn't
   * have the responsibility to answer in this context.
   *
   * @param {*} permissions the object generated by the backend permission manager with
   *   the same name.
   * @param {string} operation the operation name.
   * @param {*} context the context object on which the operation applies.
   * @param {*} workspaceId the workspaceId the permission is being requested in if
   *   there is a workspace involved, if not then this will be null.
   */
  hasPermission(permissions, operation, context, workspaceId) {}

  /**
   * The order value used to sort admin types in the sidebar menu.
   */
  getOrder() {
    return 0
  }

  /**
   * Translation mappings for all the roles that have been added by your
   * permission manager
   */
  getRolesTranslations() {
    return {}
  }
}

export class CorePermissionManagerType extends PermissionManagerType {
  static getType() {
    return 'core'
  }

  hasPermission(permissions, operation, context, workspaceId) {
    if (permissions.includes(operation)) {
      return true
    }
  }
}

export class StaffPermissionManagerType extends PermissionManagerType {
  static getType() {
    return 'staff'
  }

  hasPermission(permissions, operation, context, workspaceId) {
    if (permissions.staff_only_operations.includes(operation)) {
      return permissions.is_staff
    }
  }
}

export class WorkspaceMemberPermissionManagerType extends PermissionManagerType {
  static getType() {
    return 'member'
  }

  hasPermission(permissions, operation, context, workspaceId) {
    return permissions
  }
}

export class BasicPermissionManagerType extends PermissionManagerType {
  static getType() {
    return 'basic'
  }

  getRolesTranslations() {
    const { i18n } = this.app

    return {
      ADMIN: {
        name: i18n.t('permission.admin'),
        description: i18n.t('permission.adminDescription'),
      },
      MEMBER: {
        name: i18n.t('permission.member'),
        description: i18n.t('permission.memberDescription'),
      },
    }
  }

  hasPermission(permissions, operation, context, workspaceId) {
    // Is it an admin only operation?
    if (permissions.admin_only_operations.includes(operation)) {
      // yes, so it should be an admin of the workspace
      if (permissions.is_admin) {
        // It is!
        return true
      }
    } else {
      // It's a member and it's a non admin only operation.
      return true
    }
    // None of the above applied
    return false
  }
}

export class StaffOnlySettingOperationPermissionManagerType extends PermissionManagerType {
  static getType() {
    return 'setting_operation'
  }

  hasPermission(permissions, operation, context, workspaceId) {
    // Fetch isStaff from the auth store, so we can reactively update the permission.
    const { store } = this.app
    const isStaff = store.getters['auth/isStaff']

    // Check if the operation is in either array of operations.
    if (
      permissions.always_allowed_operations.includes(operation) ||
      permissions.staff_only_operations.includes(operation)
    ) {
      // Permission is...
      // A) allowed if the Setting it relates to is set to "everyone", or
      // B) allowed if, regardless of the Setting, the actor isStaff.
      return (
        permissions.always_allowed_operations.includes(operation) ||
        (permissions.staff_only_operations.includes(operation) && isStaff)
      )
    }
  }
}

export class AllowIfTemplateOperationPermissionManagerType extends PermissionManagerType {
  static getType() {
    return 'allow_if_template'
  }

  hasPermission(permissions, operation, context, workspaceId) {
    if (permissions.workspace_template_ids.includes(workspaceId)) {
      if (permissions.allowed_operations_on_templates.includes(operation)) {
        return true
      }
    }
    // Workspace ID `0` can be used to fake workspace objects, like for example
    // during the onboarding.
    // @TODO this is not the nicest place to allow this. decide whether we want to
    // implement it this way.
    if (workspaceId === 0 && context?._?.is_onboarding) {
      return true
    }
  }
}
