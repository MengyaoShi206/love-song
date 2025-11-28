# Love Song 婚恋匹配系统

一个用于「恋爱交友 / 婚恋匹配」场景的全栈示例项目，包含用户资料管理、匹配展示、实时聊天、广告与 VIP+ 会员等完整链路。


## 功能概览

### 用户与资料

- 用户注册 / 登录（`HomeView.vue`、`LoginView.vue`、`RegisterView.vue`）。
- 个人中心（`MainLayout.vue`）  
  - 折叠面板分区编辑：  
    - 基础信息：用户名、昵称、性别、城市、家乡、生日、身高体重、联系方式等。  
    - 生活方式：作息、饮酒、吸烟、运动频率、饮食习惯、宠物观等（`UserLifestyle`）。  
    - 择偶意向：感情目标、年龄/身高/体重区间、是否接受异地、离异/带娃等（`UserIntention`）。  
    - 问答 / 媒体 / 认证等附加资料。  
  - 查看态会对手机号、邮箱等敏感字段做掩码，并根据生日实时计算年龄。  
  - 编辑态通过表单校验规则（手机号、邮箱、身高体重区间等）保证数据合理性，保存后立即写主库并异步镜像到 Doris。
- 对隐私字段做了屏蔽展示（如手机号、邮箱部分打码、年龄由生日计算）。

### 匹配与资料展示

- 匹配中心入口（`MatchDisplayView.vue`）  
  左侧菜单统一聚合“资料展示 / 匹配资料展示 / 聊天（已匹配）”，右侧通过 Tabs 切换不同匹配来源：

- Tab 1：为您推荐（`name="recommend"`）  
  - 后端接口：`GET /user/recommend/{uid}`  
  - 调用 `RecommendService.recommend_for_user(...)` 在数据库内做多维召回与打分。  
  - 前端支持：  
    - 每页数量选择（20/40/100 条）、一键刷新推荐。  
    - 卡片展示头像、昵称、年龄、城市，“综合匹配度”百分比、推荐理由摘要。  
    - 操作：查看资料、喜欢、拉黑等（根据 `match_status` 展示按钮或标签）。

- Tab 2：喜欢你的人（`name="likedMe"`）  
  - 后端接口：`GET /user/match/liked_me/{uid}`  
  - 从 `UserLike` 表中取出“对当前用户点过喜欢”的人，并结合 `Match` 表，标记状态：  
    - `waiting`：对方喜欢你，你还没表态；  
    - `pending`：你也点过喜欢但尚未变成有效 Match；  
    - `matched`：已形成双向匹配。  
  - 前端展示对方基础资料，并提供“喜欢回去”按钮快速形成匹配。

- Tab 3：您的喜欢（`name="likes"`）  
  - 后端接口：`GET /user/match/likes/{uid}`  
  - 列出你给别人点过“喜欢”的用户，结合 `Match` 状态显示是否已双向匹配。  
  - 支持分页、查看资料、取消喜欢等操作。

- Tab 4：自定义匹配（`name="custom"`）  
  - 后端接口：`GET /user/match/custom/{uid}`  
  - 支持按性别、城市、家乡、年龄/身高/体重区间等组合筛选；若前端未传条件，则默认参考自身择偶意向给一个合理区间。  
  - 前端提供表单筛选 + 分页展示，可快速构造“我的自定义条件”下的候选列表。

- Tab 5：已双向匹配（`name="mutual"`）  
  - 后端接口：`GET /user/match/mutual/{uid}`  
  - 直接从 `Match` 表读取已激活（`active=true`）的双向关系，按创建时间排序。  
  - 前端展示“已双向匹配的人”，并提供发起聊天 / 查看资料入口。

- Tab 6：其他（保留扩展位）  
  - 预留未来玩法（例如活动报名、线下局、推荐任务等）。

- 资料详情页矩阵  
  根据来源不同拆出多种详情页，共用相似布局但保留上下文：  
  - 一般资料展示：`DisplayView.vue`（从列表/推荐点击进入）。  
  - 来自“喜欢你的人”：`DisplayLikedView.vue`。  
  - 来自“为您推荐”：`DisplayRecommendView.vue`。  
  - 来自“自定义匹配”：`DisplayCustomView.vue`。  
  - 来自“聊天入口（双向匹配）”：`DisplayChatView.vue`。  

  每个详情页大致包含：  
  - 基础信息：用户名、昵称、性别、城市、身高体重、家乡、感情状态、有无子女等。  
  - 公开资料：个性签名、个人简介、标签等。  
  - 生活方式、择偶意向、问答、媒体（照片/视频）、认证信息等板块。  
  - 顶部会根据当前双方关系展示“喜欢 / 已喜欢 / 已匹配”状态及操作按钮。

### 聊天系统

- 页面：`ChatListView.vue`（左侧列表 + 右侧会话）  
  - 左侧：  
    - 调用 `getMatchMutual` 拉取所有已双向匹配对象；  
    - 展示头像、昵称、年龄 · 城市、最后一条消息预览；  
    - 根据每个会话的未读数，在头像右下角显示徽标；  
    - 顶部显示“已双向匹配（X人），未读 Y 条”。  
  - 右侧：  
    - 当前选中对象的对话记录（`getChatHistory`）；  
    - 支持滚动加载更多历史；  
    - 文本消息、图片消息（`<el-image>` 大图预览）、文件/视频通过附件类型区分展示。

- 发送消息  
  - 文本输入框支持回车发送、多行编辑、表情插入。  
  - 表情面板通过 `emojiList` 预置常用 Emoji，点击自动插入到输入框。  
  - 附件面板：点击“加号”选择照片 / 视频 / 文件，调用 `uploadChatFile` 接口上传。  
    - 后端接口：`POST /chat/upload`（见 `backend/app/api/chat.py`），校验双方用户存在，保存文件到 `UPLOAD_ROOT/YYYYMMDD/uuid.ext`，写一条 `ChatMessage` 记录，再通过 WebSocket 推送给在线双方。  
  - 发送文本使用 `sendChatMessage`，同时写数据库并通过 WebSocket 实时分发。

- WebSocket 实时通信  
  - 后端：`backend/app/api/chat.py`  
    - 使用 `APIRouter` 暴露 WebSocket 入口；  
    - 通过连接管理器维护在线用户连接字典；  
    - 支持心跳包（`type=ping/heartbeat` → 返回 `pong`）；  
    - 收到聊天消息后写入 `ChatMessage`，并广播给会话双方。  
  - 前端在聊天页面建立单一 WebSocket 连接，监听新消息并更新当前会话与未读计数。

- 未读数徽标（全局）  
  - 组合式函数：`frontend/src/composables/useChatUnreadBadge.js`。  
  - 在登录后根据当前用户 ID 从 `sessionStorage(chat_unread_total_v1_{uid})` 中同步总未读数。  
  - 所有更新未读数的地方调用 `setTotalUnread` 写入 ref，并回写到 `sessionStorage`，`totalUnreadDisplay` 自动格式化为数字或 `99+`。  
  - 匹配中心左侧菜单的“聊天（已匹配）”和 ChatList 页面顶部都使用这套统一徽标。


### 广告与 VIP+

- 广告详情（`AdDetailView.vue`）  
  - 从路由 `:id` 读取广告 ID，调用后端拉取详情（标题、发布时间、正文内容）；  
  - 提供“返回”和“回到来源列表”按钮，`route.query.from` 允许从推荐列表、匹配中心等处跳转过来再原路返回；  
  - 对非法 ID 做前端容错（记录 warning，不强制跳转）。

- VIP+ 会员（`VipPlusView.vue`）  
  - 展示开通 VIP+ 的核心权益；
  - 权益说明：免广告聊天、更高曝光、高级筛选、专属徽章等。
  - 模拟开通流程（本地标记字段），后续可接支付 / 会员服务端。
- 业务上可结合「发起聊天需看广告 / VIP+ 免广告」等逻辑进行引流与变现。


## 技术栈

### 后端（backend）

- Python 3 + FastAPI（REST API + WebSocket）。
- SQLAlchemy / Pydantic 进行 ORM 与数据校验。
- 在线事务库：SQLite / MySQL，用于用户、资料、匹配关系、聊天等核心业务表。
- 分析库：Apache Doris，用于埋点日志、聊天明细、行为数据等的明细存储与 OLAP 分析：
  - 通过独立的写入脚本 / 多写入器（multi-writer）异步将在线库数据同步到 Doris；
  - 适合做推荐特征统计、留存/转化漏斗、广告点击分析等。


- 核心模块  
  - `backend/app/api/user.py`（本仓库中为 `user_api.py`）：  
    - 登录/注册、主资料接口 `/main/{uid}`；  
    - 资料完善度计算与打分；  
    - 匹配相关接口：  
      - `/match/likes/{uid}`：我喜欢的人；  
      - `/match/liked_me/{uid}`：喜欢我的人；  
      - `/match/mutual/{uid}`：已双向匹配；  
      - `/match/custom/{uid}`：自定义匹配筛选；  
      - `/recommend/{uid}`：为您推荐。  
    - 喜欢逻辑（`POST /like`）会自动检查是否形成 `Match`，避免重复写入。  
  - `backend/app/api/chat.py`：  
    - 聊天 WebSocket 入口（心跳、消息分发）；  
    - `POST /upload`：聊天附件上传并写入 `ChatMessage`；  
    - 聊天历史记录查询（供前端 `getChatHistory` 使用）。  
  - `backend/app/scripts/create_chat_table.py`：  
    - 使用 `ChatMessage.__table__.create(checkfirst=True)` 在主库创建聊天消息表。

### 前端（frontend）

- 框架与 UI  
  - Vue 3 + Vue Router。  
  - Element Plus 作为 UI 组件库，广泛用于表单、卡片、布局、Skeleton 等。  

- 路由配置（`frontend/src/router/index.js`）  
  - `/` → `HomeView.vue`  
  - `/register` → 注册页  
  - `/login` → 登录页  
  - `/main` → 个人中心  
  - `/match` → 匹配中心首页（`MatchDisplayView.vue`）  
  - `/chat-list` → 已匹配聊天列表 + 对话窗（`ChatListView.vue`）  
  - `/display/:uid`、`/display-liked/:uid`、`/display-recommend/:uid`、`/display-custom/:uid`、`/display-chat/:uid` 等若干资料详情路由  
  - `/ad/:id` → 广告详情页  
  - `/vip-plus` → VIP+ 开通页  
  - 未知路径统一重定向到 `/`。

- API 与业务封装  
  - `@/api`：统一封装后端接口，如：  
    - `getMatchMutual`、`getChatHistory`、`sendChatMessage`、`uploadChatFile` 等聊天相关；  
    - 匹配与资料接口（为您推荐 / 喜欢你的人 / 您的喜欢 / 自定义匹配）。  
  - 组合式函数：  
    - `useChatUnreadBadge`：管理全局聊天未读总数。  
    - `useAdGateForChat`：处理聊天发起前的广告闸门逻辑。  
  - 组件：  
    - `ForcedAdDialog.vue`：强制广告弹窗组件。

### 数据层（data）

- `data/` 目录用于存放示例数据、模型输出或离线分析结果（具体内容根据实际项目填充）。
- 后端可通过自定义脚本将行为日志、聊天等写入该目录或外部数据仓库做分析。
