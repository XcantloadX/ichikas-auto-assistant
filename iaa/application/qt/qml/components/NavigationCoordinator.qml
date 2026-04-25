import QtQuick

Item {
    id: root
    visible: false

    required property var settingsCtrl
    required property var unsavedChangesDialog

    property var pendingActionRunner: null
    property string pendingActionLabel: ""

    function isDirty() {
        return root.settingsCtrl ? root.settingsCtrl.isDirty() : false
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
        if (root.settingsCtrl && root.settingsCtrl.save()) {
            root.runPendingAction()
        }
    }

    function discardAndContinuePendingAction() {
        if (root.settingsCtrl) {
            root.settingsCtrl.discard()
        }
        root.runPendingAction()
    }
}
