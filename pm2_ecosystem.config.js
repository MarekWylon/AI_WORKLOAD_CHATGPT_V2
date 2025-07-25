module.exports = {
  apps: [{
    name: "Workload_MAIN",
    script: "workload_main.py",
    interpreter: "/root/dev/Workload_ChatGPT/.venv/bin/python",
    cwd: "/root/dev/Workload_ChatGPT",
    watch: false,
    instance_var: 'INSTANCE_ID',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    output: '/var/log/workload_chatgpt.log',
    error: '/var/log/workload_chatgpt.log',
    merge_logs: true,
    env: {
      "PATH": "/root/dev/Workload_ChatGPT/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    }
  }]
}
