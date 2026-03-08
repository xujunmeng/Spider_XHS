# 🕷️ Spider_XHS 项目架构流程说明

## 一、项目概述

**Spider_XHS** 是一个专业的小红书数据采集解决方案，支持：
- 笔记爬取（无水印图片/视频）
- 用户主页信息采集
- 搜索功能（支持多种排序和筛选）
- 评论采集
- 数据导出（Excel/Media）

---

## 二、项目结构图

```
Spider_XHS/
├── 📁 apis/                    # API接口层
│   ├── __init__.py
│   ├── xhs_pc_apis.py         # PC端小红书API（核心）
│   └── xhs_creator_apis.py    # 创作者平台API
│
├── 📁 xhs_utils/               # 工具函数层
│   ├── __init__.py
│   ├── xhs_util.py            # PC端签名/请求工具
│   ├── xhs_creator_util.py    # 创作者平台工具
│   ├── cookie_util.py         # Cookie转换工具
│   ├── data_util.py           # 数据处理与存储
│   └── common_util.py         # 通用初始化工具
│
├── 📁 static/                  # 静态资源（JS算法）
│   ├── xhs_xs_xsc_56.js       # XS/XT/XS-Common签名算法(v56)
│   ├── xhs_creator_xs.js      # 创作者平台签名算法
│   ├── xhs_xray.js            # X-Ray TraceID生成
│   └── xs-common-1128.js      # XS-Common算法备用
│
├── 📁 author/                  # 作者信息/赞助码
├── 📁 static/                  # 前端静态资源
├── main.py                     # 主入口（爬虫调度）
├── .env                        # 环境配置（Cookie）
├── requirements.txt            # Python依赖
└── Dockerfile                  # 容器化配置
```

---

## 三、核心架构流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据采集流程架构                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐
│   配置层    │────▶│   签名层    │────▶│       API请求层         │
│   (.env)    │     │  (JS算法)   │     │   (apis/xhs_pc_apis)    │
└─────────────┘     └─────────────┘     └─────────────────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐
│   存储层    │◀────│   处理层    │◀────│       数据获取层        │
│ (Excel/     │     │ (data_util) │     │    (小红书服务器)       │
│  Media)     │     │             │     │                         │
└─────────────┘     └─────────────┘     └─────────────────────────┘
```

---

## 四、各层详细说明

### 1️⃣ 配置层 (.env)

```
# .env 文件
COOKIES='acw_tc=xxx; a1=xxx; web_session=xxx; ...'
```

**关键Cookie字段**：
- `a1` - 用户标识，用于生成签名
- `web_session` - 会话凭证
- `xsecappid` - 安全验证

---

### 2️⃣ 签名层 (xhs_utils/xhs_util.py)

**核心功能**：生成小红书反爬验证所需的请求头

| 生成字段 | 说明 | 来源 |
|---------|------|------|
| `X-s` | 请求签名 | JS算法 (xhs_xs_xsc_56.js) |
| `X-t` | 时间戳 | JS算法 |
| `X-s-common` | 通用签名 | JS算法 |
| `X-b3-traceid` | 追踪ID | Python随机生成 |
| `X-xray-traceid` | 射线追踪ID | JS算法 (xhs_xray.js) |

**签名调用链**：
```
generate_request_params()
    ├── trans_cookies()          # Cookie字符串转字典
    ├── generate_headers()
    │     ├── generate_xs_xs_common()  # 调用JS生成X-s/X-t/X-s-common
    │     ├── generate_x_b3_traceid()  # 生成追踪ID
    │     └── get_request_headers_template() # 获取请求头模板
    └── return headers, cookies, data
```

**JS算法执行**（使用 PyExecJS）：
```python
js = execjs.compile(open('static/xhs_xs_xsc_56.js').read())
ret = js.call('get_request_headers_params', api, data, a1, method)
xs, xt, xs_common = ret['xs'], ret['xt'], ret['xs_common']
```

---

### 3️⃣ API请求层 (apis/xhs_pc_apis.py)

**XHS_Apis 类 - 核心API列表**：

| 方法 | 功能 | 接口路径 |
|-----|------|---------|
| `get_note_info()` | 获取笔记详情 | `/api/sns/web/v1/feed` |
| `get_user_all_notes()` | 获取用户所有笔记 | `/api/sns/web/v1/user_posted` |
| `get_user_all_like_note_info()` | 获取用户喜欢的笔记 | `/api/sns/web/v1/note/like/page` |
| `get_user_all_collect_note_info()` | 获取用户收藏的笔记 | `/api/sns/web/v2/note/collect/page` |
| `search_some_note()` | 搜索笔记 | `/api/sns/web/v1/search/notes` |
| `get_note_all_comment()` | 获取笔记评论 | `/api/sns/web/v2/comment/page` |
| `get_note_no_water_img()` | 获取无水印图片 | 静态页面解析 |
| `get_note_no_water_video()` | 获取无水印视频 | 静态页面解析 |

**请求流程**：
```python
def get_note_info(url, cookies_str, proxies):
    # 1. 解析URL获取note_id和xsec_token
    note_id = parse_url(url)
    
    # 2. 构建请求数据
    data = {"source_note_id": note_id, "xsec_token": xsec_token, ...}
    
    # 3. 生成签名请求头
    headers, cookies, data = generate_request_params(cookies_str, api, data, 'POST')
    
    # 4. 发送请求
    response = requests.post(base_url + api, headers=headers, data=data, cookies=cookies, proxies=proxies)
    
    # 5. 返回结果
    return response.json()
```

---

### 4️⃣ 数据处理层 (xhs_utils/data_util.py)

**核心功能**：

| 函数 | 功能 |
|-----|------|
| `handle_note_info()` | 解析笔记原始数据，提取关键字段 |
| `handle_user_info()` | 解析用户原始数据 |
| `handle_comment_info()` | 解析评论数据 |
| `download_note()` | 下载笔记的媒体文件 |
| `save_to_xlsx()` | 保存数据到Excel |

**笔记数据结构**：
```python
{
    'note_id': '笔记ID',
    'note_url': '笔记链接',
    'note_type': '图集/视频',
    'user_id': '用户ID',
    'nickname': '昵称',
    'title': '标题',
    'desc': '描述',
    'liked_count': '点赞数',
    'collected_count': '收藏数',
    'comment_count': '评论数',
    'share_count': '分享数',
    'video_addr': '视频地址',
    'image_list': ['图片地址1', '图片地址2', ...],
    'tags': ['标签1', '标签2'],
    'upload_time': '上传时间',
    'ip_location': 'IP归属地'
}
```

---

### 5️⃣ 主入口层 (main.py)

**Data_Spider 类 - 业务封装**：

| 方法 | 功能 | 使用场景 |
|-----|------|---------|
| `spider_note()` | 爬取单个笔记 | 单笔记采集 |
| `spider_some_note()` | 爬取多个笔记 | 批量笔记采集 |
| `spider_user_all_note()` | 爬取用户所有笔记 | 用户主页采集 |
| `spider_some_search_note()` | 按关键词搜索采集 | 关键词搜索 |

---

## 五、数据流转图

```
┌─────────────────────────────────────────────────────────────────┐
│                        单次请求完整流程                          │
└─────────────────────────────────────────────────────────────────┘

用户调用
    │
    ▼
┌─────────────────┐
│ main.py         │  Data_Spider.spider_note(note_url, cookies, ...)
│ 业务层入口       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ xhs_pc_apis.py  │  get_note_info(url, cookies)
│ API封装层       │  ├── 解析URL获取note_id/xsec_token
│                 │  ├── 构建请求数据data
│                 │  └── 调用generate_request_params()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ xhs_util.py     │  generate_request_params(cookies_str, api, data, method)
│ 签名生成层      │  ├── trans_cookies()  # Cookie转字典
│                 │  ├── generate_headers(a1, api, data, method)
│                 │  │     ├── generate_xs_xs_common() 
│                 │  │     │     └── 调用xhs_xs_xsc_56.js生成X-s/X-t/X-s-common
│                 │  │     ├── generate_x_b3_traceid()
│                 │  │     └── generate_xray_traceid()
│                 │  └── 返回headers, cookies, data
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ requests        │  requests.post(base_url + api, headers=headers, ...)
│ HTTP请求        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 小红书服务器     │  返回JSON数据
│ edith.xiaohongshu.com │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ data_util.py    │  handle_note_info(data)
│ 数据处理层      │  ├── 提取关键字段
│                 │  ├── 转换时间戳
│                 │  └── 返回结构化数据
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ 存储层           │     │ 存储层           │
│ save_to_xlsx()  │     │ download_note() │
│ Excel文件       │     │ 媒体文件(图片/视频)│
└─────────────────┘     └─────────────────┘
```

---

## 六、反爬机制应对

| 反爬手段 | 应对方案 |
|---------|---------|
| **X-s 签名验证** | 通过 JS 逆向，使用 `xhs_xs_xsc_56.js` 生成正确签名 |
| **X-t 时间戳** | JS算法生成，与服务器时间同步 |
| **X-s-common** | 同上，用于通用接口验证 |
| **X-b3-traceid** | Python随机生成16位十六进制字符串 |
| **X-xray-traceid** | 通过 `xhs_xray.js` 算法生成 |
| **Cookie验证** | 使用登录后的有效Cookie |
| **IP限制** | 支持 `proxies` 参数配置代理 |
| **频率限制** | 使用 `retry` 装饰器实现自动重试 |

---

## 七、创作者平台架构 (apis/xhs_creator_apis.py)

**XHS_Creator_Apis 类**：

| 方法 | 功能 | 接口 |
|-----|------|------|
| `get_publish_note_info()` | 获取已发布笔记 | `/web_api/sns/v5/creator/note/user/posted` |
| `get_all_publish_note_info()` | 获取全部已发布笔记 | 分页循环获取 |

**签名差异**：
- 使用 `xhs_creator_xs.js` 生成签名
- 请求头略有不同（Origin/Referer指向creator.xiaohongshu.com）

---

## 八、使用示例

```python
# main.py 使用示例

# 1. 初始化
cookies_str, base_path = init()
data_spider = Data_Spider()

# 2. 爬取单个笔记
notes = ['https://www.xiaohongshu.com/explore/xxx?xsec_token=xxx']
data_spider.spider_some_note(notes, cookies_str, base_path, 'all', 'test')

# 3. 爬取用户所有笔记
user_url = 'https://www.xiaohongshu.com/user/profile/xxx?xsec_token=xxx'
data_spider.spider_user_all_note(user_url, cookies_str, base_path, 'all')

# 4. 搜索关键词
data_spider.spider_some_search_note(
    query="榴莲",           # 搜索关键词
    require_num=10,         # 获取数量
    cookies_str=cookies_str,
    base_path=base_path,
    save_choice='all',      # all/media/excel
    sort_type_choice=0,     # 0综合 1最新 2最多点赞 3最多评论 4最多收藏
    note_type=0,            # 0不限 1视频 2图文
    note_time=0,            # 0不限 1一天内 2一周内 3半年内
    note_range=0            # 0不限 1已看过 2未看过 3已关注
)
```

---

## 九、技术栈

| 技术 | 用途 |
|-----|------|
| **Python 3.7+** | 主开发语言 |
| **Node.js 18+** | JS执行环境（用于签名算法） |
| **PyExecJS** | Python调用JavaScript |
| **requests** | HTTP请求 |
| **loguru** | 日志记录 |
| **openpyxl** | Excel文件操作 |
| **retry** | 自动重试机制 |
| **python-dotenv** | 环境变量管理 |

---

## 十、总结

该项目采用**分层架构设计**：
- **API层**负责与小红书服务器通信
- **工具层**处理签名生成、数据解析等通用逻辑
- **业务层**（main.py）提供高层次的业务封装
- **静态资源层**存放逆向的JS算法

核心难点在于**签名算法的JS逆向**，通过 `PyExecJS` 调用Node.js执行环境来生成合法的请求签名，从而绕过小红书的反爬机制。
