import QtQuick

Item {
    id: root
    visible: false

    required property var settingsCtrl
    required property var prefsCtrl
    required property var unsavedChangesDialog

    property var pendingActionRunner: null
    property string pendingActionLabel: ""

    function isDirty() {
        var settingsDirty = root.settingsCtrl ? root.settingsCtrl.isDirty() : false
        var prefsDirty = root.prefsCtrl ? root.prefsCtrl.isDirty() : false
        return settingsDirty || prefsDirty
    }

    function clearPendingGuardedAction() {
        root.pendingActionRunner = null
        root.pendingActionLabel = ""
    }

    function runPendingAction() {
        var runner = root.pendingActionRunner
        root.clearPendingGuardedAction()
        if (typeof runner === "function") {
            runner()
        }
    }

    function requestGuardedAction(label, runner) {
        if (typeof runner !== "function") {
            return
        }
        if (!root.isDirty()) {
            runner()
            return
        }
        root.pendingActionRunner = runner
        root.pendingActionLabel = label || "继续此操作"
        root.unsavedChangesDialog.actionLabel = root.pendingActionLabel
        root.unsavedChangesDialog.open()
    }

    function saveAndContinuePendingAction() {
        if (root.settingsCtrl && root.settingsCtrl.isDirty()) {
            root.settingsCtrl.save()
        }
        if (root.prefsCtrl && root.prefsCtrl.isDirty()) {
            root.prefsCtrl.save()
        }
        root.runPendingAction()
    }

    function discardAndContinuePendingAction() {
        if (root.settingsCtrl) {
            root.settingsCtrl.discard()
        }
        if (root.prefsCtrl) {
            root.prefsCtrl.discard()
        }
        root.runPendingAction()
    }
}
