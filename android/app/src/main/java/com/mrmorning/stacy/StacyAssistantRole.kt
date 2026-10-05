package com.mrmorning.stacy

import android.app.Activity
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.os.Build

object StacyAssistantRole {
    const val REQUEST_CODE = 7401

    fun isAvailable(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false
        val roleManager = context.getSystemService(RoleManager::class.java)
        return roleManager?.isRoleAvailable(RoleManager.ROLE_ASSISTANT) == true
    }

    fun isHeld(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false
        val roleManager = context.getSystemService(RoleManager::class.java)
        return roleManager?.isRoleHeld(RoleManager.ROLE_ASSISTANT) == true
    }

    fun request(activity: Activity) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return
        val roleManager = activity.getSystemService(RoleManager::class.java) ?: return
        if (!roleManager.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) return
        activity.startActivityForResult(
            roleManager.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT),
            REQUEST_CODE
        )
    }
}
