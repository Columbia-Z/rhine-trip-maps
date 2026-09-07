# 莱茵两城行程地图

公开的杜塞尔多夫、科隆互动地图，使用本地 Leaflet 库、Flask 和 Gunicorn，
部署目标为 **Azure App Service（Linux）**，不是 Static Web Apps。无需 Node.js 或前端构建。

**部署地址**：[主站](https://rhine-trip-maps-columbia-z.azurewebsites.net/) ·
[杜塞尔多夫](https://rhine-trip-maps-columbia-z.azurewebsites.net/dusseldorf.html) ·
[科隆](https://rhine-trip-maps-columbia-z.azurewebsites.net/cologne.html)。
以上为目标访问地址，实际可用性取决于发布状态。

访问 `/` 会转到 `/dusseldorf.html`；另一页为 `/cologne.html`。
保留旗标地点、日期筛选、步行道路几何、公共交通示意线、导航链接、预算和来源说明。
页面右上角可下载 `/trip-maps.zip`，解压后直接打开任一城市 HTML。
脚本、样式和路线数据均随包附带，**OpenStreetMap 底图和外部导航仍需联网**；
断网时页面会提示，地点和路线数据仍可查看。ZIP 内的下载按钮无需使用，
要重新取得 ZIP 请回到在线站点。

## 行程及信息边界

- 2026 年 9 月 19 日中午抵达 DUS，杜塞尔多夫住一晚。
- 9 月 20 日转往科隆，住 9 月 20、21 日两晚，22 日退房。
- 9 月 22 日 23:15 从 CGN 飞都柏林，落地可能是 9 月 23 日凌晨，以机票为准。

除明确注明都柏林当地时间外，行程均按德国当地时间。图中酒店仅为住宿参考区，
不是已预订住宿；班次、营业时间、航班和票价均须出发前通过官方渠道确认。
每人交通预算约 €40–50，不含机票、住宿和景点门票；跨城票价是预留区间，
不是指定起讫站的已核实报价，不要重复购买已被有效日票覆盖的车程。
目前 17 段步行中最长 999 米，**单段不超过 1 km 不代表每日只走 1 km**，
也不包含馆内、站内、实际酒店入口及临时绕路。公共交通连线是示意，不是实时导航。

页面保留 OpenStreetMap 署名及数据来源，Leaflet 的 BSD 2-Clause 许可见
[`public/LEAFLET-LICENSE.txt`](public/LEAFLET-LICENSE.txt)。仓库不包含订单、个人资料、
源数据缓存或已订酒店信息；后续修改也应保持公开内容边界。

## 本地运行

使用 Python 3.12；代码也支持 Python 3.11，CI 覆盖两者。在仓库根目录执行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
gunicorn --bind=127.0.0.1:8000 --timeout 120 app:app
```

打开 `http://127.0.0.1:8000/`，按 Ctrl-C 停止。Gunicorn 适用于 Linux/macOS；
Windows 可使用 WSL。不要在生产使用 Flask 开发服务器或 debug 模式。

```sh
python -m unittest discover -s tests -v
curl --fail http://127.0.0.1:8000/healthz
```

`GET /healthz` 返回 `{"status":"ok"}`，仅检查进程可响应，不检查第三方底图、
班次或外部服务。支持 HEAD；健康响应不缓存，静态资源通过 ETag 重新验证。
服务只开放 `public/` 内明确列出的 9 个文件，不开放任意目录浏览、
服务端源码、配置或仓库文件。

## 更新地图与 ZIP

编辑 `public/` 内公开文件后，在已安装依赖的虚拟环境中执行：

```sh
python -m scripts.build_zip
python -m scripts.build_zip --check
python -m unittest discover -s tests -v
```

将更新后的公开文件和 `public/trip-maps.zip` 一起提交。ZIP 只含两个 HTML、
`app.js`、`data.js`、`style.css`、`leaflet.js`、`leaflet.css` 和 Leaflet 许可证，
不会递归包含 ZIP 自身、服务端、源码缓存或凭据。
文件顺序、时间戳和权限固定；使用 ZIP 的无压缩存储方式，使同样的输入可在不同
Python/zlib 版本间逐字节重现。测试检查归档与公开文件一致、行程关键事实、
路线引用和所有步行段的 1000 米上限；有意更改行程时也要更新对应断言。

## Azure App Service 配置

以下资源和身份由管理员在仓库外配置；工作流**不会创建资源、修改计费或设置凭据**。

| 项目 | 要求 |
| --- | --- |
| 服务 | Azure App Service，Linux，B1，Central US |
| Python 运行时 | `PYTHON\|3.12` |
| 启动命令 | `gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app` |
| 应用设置 | `SCM_DO_BUILD_DURING_DEPLOYMENT=true` |
| 可用性 | 建议启用 HTTPS Only、Always On，健康检查路径为 `/healthz` |

使用 ZIP Deploy 和远程 Oryx 构建。Oryx 从 ZIP 根目录的 `requirements.txt`
安装 Linux/Python 3.12 依赖；不上传本地 `.venv` 或 `.python_packages`。
不要启用 `WEBSITE_RUN_FROM_PACKAGE`，它与此处的远程构建部署方式不兼容。
启动命令中的 `app:app` 指根目录 `app.py` 的 Flask WSGI 对象。

GitHub 仓库 **Settings → Secrets and variables → Actions → Variables** 需要：

| 仓库 variable | 用途 |
| --- | --- |
| `AZURE_CLIENT_ID` | 部署身份的客户端 ID |
| `AZURE_TENANT_ID` | 身份所在租户 |
| `AZURE_SUBSCRIPTION_ID` | 目标订阅 |
| `AZURE_WEBAPP_NAME` | 已创建的 App Service 应用名 |

管理员应为部署身份设置目标应用所需的最小部署权限及 GitHub OIDC 联合身份：
issuer 为 `https://token.actions.githubusercontent.com`，
audience 为 `api://AzureADTokenExchange`，
subject 为 `repo:Columbia-Z/rhine-trip-maps:ref:refs/heads/main`。
此工作流没有配置 GitHub environment；若日后添加 environment，必须同步调整联合身份
subject。无需 publish profile、客户端密钥或用户交互登录，不要将它们提交到仓库。

## 费用与停止计费

Central US 的 Linux B1 单实例公开按需价格为 **USD 0.018/小时**，
按每月 730 小时估算约 **USD 13.14**，流量、税费等另计。此金额仅为估算，
实际费用以 Azure 当前价格和账单为准，**不表示已核实订阅的 credit 余额**。

**仅停止 WebApp 不会停止 App Service Plan 计费。** 不再使用时，应由用户自行确认
资源及依赖均不再需要后，删除专用 App Service Plan 或整个专用资源组；
删除资源组也会删除其中其他资源。本仓库和部署工作流不会自动执行这些删除操作。

## 部署流程

`.github/workflows/azure.yml` 在 PR、main push 和手动运行时执行 Python 3.11/3.12 测试。
只有 **main push 或选择 main 的 workflow_dispatch** 在全部测试通过后才部署；
PR 和非 main 的手动运行均不会获得部署令牌。仅 deploy job 有 `id-token: write`，
其他权限为 `contents: read`，Actions 使用固定提交版本。
缺少任一 Azure variable 时会明确报错并停止，绝不猜测应用名或凭据。

部署使用 `azure/login` OIDC 和 `azure/webapps-deploy`。本地也可检查相同的部署包：

```sh
python -m scripts.build_zip --deployment
python -m zipfile -l dist/app-service.zip
```

部署 ZIP 根目录只有 `app.py`、`requirements.txt` 和 `public/` 下的明确公开文件
（包含可下载的 `trip-maps.zip`），没有额外父目录、测试、维护脚本或仓库配置。
`dist/` 与部署归档已被忽略，不要提交。归档前会拒绝过期的便携 ZIP。
管理员配置好 Azure 和 variables 后，合并 PR 到 main 即触发发布；
也可在 Actions 选择该工作流，选 main 后点击 Run workflow。
发布结束后访问应用 URL 下的 `/healthz`、两城页面和下载链接。
如果失败，先查看 Actions 中缺失变量/OIDC/部署错误，再检查 App Service
部署日志和启动日志，核对运行时、启动命令及 Oryx 设置。
