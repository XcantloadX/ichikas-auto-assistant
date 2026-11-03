import Java from 'frida-java-bridge';

rpc.exports = {
    load(path: string): string {
        let result = 'no-result';
        Java.perform(function () {
            try {
                const at = Java.use('android.app.ActivityThread');
                const app = at.currentApplication();
                const runtime = Java.use('java.lang.Runtime').getRuntime();
                // load0(Class fromClass, String filename)：绕开 caller-class 检查
                runtime.load0(app.getClass(), path);
                result = 'ok';
            } catch (e: any) {
                result = String(e) + ' | stack: ' + (e && e.stack ? e.stack.split('\n').slice(0, 3).join(' / ') : '');
            }
        });
        return result;
    }
};
