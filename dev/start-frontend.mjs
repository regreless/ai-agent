import { createRequire as create_require } from 'node:module'
import { dirname, resolve } from 'node:path'
import { fileURLToPath as file_url_to_path, pathToFileURL as path_to_file_url } from 'node:url'

const script_dir = dirname(file_url_to_path(import.meta.url))
const frontend_dir = resolve(process.env.FRONTEND_DIR || resolve(script_dir, '../../enterprise_ai_agent_platform_real/frontend'))
const backend_url = process.env.BACKEND_URL || 'http://localhost:8000'
const frontend_port = Number(process.env.FRONTEND_PORT || 5173)
const frontend_require = create_require(resolve(frontend_dir, 'package.json'))
const { createServer: create_server, loadConfigFromFile: load_config_from_file, mergeConfig: merge_config } =
  await import(path_to_file_url(frontend_require.resolve('vite')).href)

// Load the existing frontend configuration without writing to the frontend project.
const loaded_config = await load_config_from_file(
  { command: 'serve', mode: 'development' },
  undefined,
  frontend_dir,
)
const server_config = merge_config(loaded_config?.config || {}, {
  configFile: false,
  root: frontend_dir,
  server: {
    host: '0.0.0.0',
    port: frontend_port,
    strictPort: true,
    proxy: {
      '/api': { target: backend_url, changeOrigin: true },
    },
  },
})

const dev_server = await create_server(server_config)
await dev_server.listen()
dev_server.printUrls()
console.log(`/api -> ${backend_url}`)

async function stop_server() {
  await dev_server.close()
  process.exit(0)
}

process.once('SIGINT', stop_server)
process.once('SIGTERM', stop_server)
