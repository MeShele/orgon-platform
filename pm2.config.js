module.exports = {
  apps: [
    {
      name: 'orgon-backend',
      script: '/bin/bash',
      args: '-c "cd /root/ORGON && source /root/ORGON/venv/bin/activate && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"',
      cwd: '/root/ORGON',
      env_file: '/root/ORGON/.env',
      env: {
        PYTHONPATH: '/root/ORGON',
        DATABASE_URL: 'postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require',
        JWT_SECRET_KEY: 'Z2tbM8sDtVfv-QPE1YB0x-5G9Tf_LhqTrKCQ15O9GzY',
        SAFINA_EC_PRIVATE_KEY: 'b7d9b51eda54d664366d74c1b1a4ed2ca9e1abed646732bfb83b141f22df3b39',
        ORGON_ADMIN_TOKEN: 'x5tKusjY8jMvzKe2esNLnpzVtJywXWVkXx7Sg-X5GHk'
      },
      log_file: '/root/ORGON/logs/backend.log',
      error_file: '/root/ORGON/logs/backend-error.log',
      out_file: '/root/ORGON/logs/backend-out.log',
      max_memory_restart: '500M',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false
    }
  ]
};