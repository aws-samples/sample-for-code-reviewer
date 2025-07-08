templates = [
	{
		"name": "通用-数据库主从设计问题（简易版）",
		"type": "whole",
		"system": "你是一位资深的代码评审员，你会严格按照要求进行代码评审，不会擅自超越范围，不会编造，会保持客观，并且给出充足的理由。",
		"config": [
			{
				"name": "requirement",
				"preamble": "这个项目使用了主从数据库架构，具有以下要求:",
				"value": "- 写操作必须使用主数据库；\n- 对于同一个实体，如果需要在写入后立即读取，必须使用主数据库，而不能使用从库。注意，加载多行数据也属于读操作；\n- 在其他读取场景下，必须使用从数据库；\n"
			},
			{
				"name": "task",
				"preamble": "你的任务如下：",
				"value": "- 请检查我的代码是否符合主从数据库设计原则。你应该递归地追踪代码调用链，进行更深入的验证。"
			},
			{
				"name": "output",
				"preamble": "输出格式要求如下：",
				"value": "```json\n[\n  {\n    \"title\": \"summary your finding, less than 30 words, in Chinese, no QUOTES and backslashes symbol here\",\n    \"content\": \"your finding, in Chinese, no QUOTES and backslashes symbol here\", \n    \"filepath\": \"filepath @ line number range, no QUOTES and backslashes symbol here\"\n  },\n  // other findings...\n]\n```\nIn field content, you must explain why it is incorrect, provide evidence. must display code snippets in markdown code block. must tell how to improve. This part should be as much detail as possible, provide evidence to support your conclusion. \n\n这是一个好的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个潜在的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n\n这是一个坏的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个名为\\\"追踪者\\\"的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n因为在「名为\\\"追踪者\\\"的安全漏洞」中出现了双引号，并且「{\\\\n    doSomethingUnsafe();」中\"\\\\n\"是不对的。\n"
			},
			{
				"name": "other",
				"preamble": "",
				"value": "请逐步思考！"
			},
			{
				"name": "response",
				"preamble": "注意：",
				"value": "- 请将你的结论输出成为JSON形式，填写在<output></output>标签中。标签中的内容我将通过JSON来解析，千万不要放置非JSON内容。\n- 你的结论是写进JSON Field中的，你要保证你输出的JSON field的正确性，尤其反斜杠和双引号问题不应该出现\n- 你需要在output标签外部指出违反了我的规范中的那些内容。\n"
			}
		]
	},
	{
		"name": "Java样板-数据库主从问题（完整版）",
		"type": "whole",
		"system": "你是一位资深的代码评审员，你会严格按照要求进行代码评审，不会擅自超越范围，不会编造，会保持客观，并且给出充足的理由。",
		"config": [
			{
				"name": "business",
				"preamble": "项目信息如下：",
				"value": "项目是一个记账业务系统，向记账App提供restful API接口，提供给C端用户使用。"
			},
			{
				"name": "sql",
				"preamble": "数据库表结构如下：",
				"value": "DROP DATABASE IF EXISTS great;\n  CREATE DATABASE great;\n  USE great;\n\n  DROP TABLE IF EXISTS great_user;\n  CREATE TABLE great_user (\n    id INT AUTO_INCREMENT PRIMARY KEY,\n    username VARCHAR(50) NOT NULL UNIQUE,\n    nickname VARCHAR(50) NOT NULL,\n    password CHAR(32) NOT NULL,\n    last_login_time DATETIME\n  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n  DROP TABLE IF EXISTS great_bill_category;\n  CREATE TABLE great_bill_category (\n    id INT AUTO_INCREMENT PRIMARY KEY,\n    name VARCHAR(50) NOT NULL UNIQUE,\n    description VARCHAR(255)\n  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n  DROP TABLE IF EXISTS great_bill_item;\n  CREATE TABLE great_bill_item (\n    id INT AUTO_INCREMENT PRIMARY KEY,\n    user_id INT NOT NULL,\n    category_id INT NOT NULL,\n    bill_date DATE NOT NULL,\n    bill_type VARCHAR(10) NOT NULL,\n    amount INT NOT NULL,\n    description VARCHAR(255)\n  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
			},
			{
				"name": "design",
				"preamble": "主要设计思想如下：",
				"value": "项目的主要对象：\n  - 用户，User\n    - 用户名称，username\n    - 用户昵称，nickname\n    - 用户密码，password，MD5加密形式\n    - 上次登录时间\n  - 账务类别，Bill Category\n    - 类别名称\n    - 类别描述\n  - 账户明细，Bill Item\n    - 用户ID，记录用户的ID\n    - 账务类别ID，记录账务类别的ID\n    - 费用日期\n    - 费用类别，字符串类型，值：income/expense\n    - 费用金额，用整形保存，以人民币的分为单位存储\n    - 费用描述\n  数据库设计的要求是：\n  - 采用MySQL InnoDB\n  - 数据库名称为great\n  - 每一张数据库表都需要带有前缀great_\n  - 主键为自增int类型\n  - 不要使用FOREIGN KEY的设计\n  - 数据库和表都要先Drop再创建\n  - 数据库设计要采用行业常见规范，并且符合最佳实践\n"
			},
			{
				"name": "web_design",
				"preamble": "Web工程设计思想如下：",
				"value": "- 项目名字叫做Great，项目主类叫App.java\n  - 使用Maven构建项目，按照Maven规范组织项目\n  - 基础包地址是demo.great\n  - 采用MVC架构，具有Controller、Service、Dao层，需要目录，但先不要Java和XML文件。\n  - 使用SpringBoot 3.1.x\n  - 项目监听8080端口，提供HTTP服务\n  - ORM层使用MyBatis来实现\n  - 数据库采用MySQL\n  - 需要进行UnitTest\n  - 需要用到SL4J记录日志\n  - pom中把需要的依赖都加上\n  - 配置文件叫做application.properties，必要的配置先填进去\n  - 必要的目录都建立起来，例如MyBatis的Mapper分为XML和Java\n  - 注意，MyBatis的Mapper如果需要被扫描，需要有所配置"
			},
			{
				"name": "requirement",
				"preamble": "这个项目使用了主从数据库架构，具有以下要求:",
				"value": "- 写操作必须使用主数据库；\n- 对于同一个实体，如果需要在写入后立即读取，必须使用主数据库，而不能使用从库。注意，加载多行数据也属于读操作；\n- 在其他读取场景下，必须使用从数据库；\n"
			},
			{
				"name": "task",
				"preamble": "你的任务如下：",
				"value": "- 请检查所有Service是否符合主从数据库设计原则。你应该递归地追踪代码调用链，进行更深入的验证。"
			},
			{
				"name": "output",
				"preamble": "输出格式要求如下：",
				"value": "```json\n[\n  {\n    \"title\": \"summary your finding, less than 30 words, in Chinese, no QUOTES and backslashes symbol here\",\n    \"content\": \"your finding, in Chinese, no QUOTES and backslashes symbol here\", \n    \"filepath\": \"filepath @ line number range, no QUOTES and backslashes symbol here\"\n  },\n  // other findings...\n]\n```\nIn field content, you must explain why it is incorrect, provide evidence. must display code snippets in markdown code block. must tell how to improve. This part should be as much detail as possible, provide evidence to support your conclusion. \n\n这是一个好的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个潜在的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n\n这是一个坏的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个名为\\\"追踪者\\\"的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n因为在「名为\\\"追踪者\\\"的安全漏洞」中出现了双引号，并且「{\\\\n    doSomethingUnsafe();」中\"\\\\n\"是不对的。\n"
			},
			{
				"name": "other",
				"preamble": "",
				"value": "请逐步思考！"
			},
			{
				"name": "response",
				"preamble": "注意：",
				"value": "- 请将你的结论输出成为JSON形式，填写在<output></output>标签中。标签中的内容我将通过JSON来解析，千万不要放置非JSON内容。\n- 你的结论是写进JSON Field中的，你要保证你输出的JSON field的正确性，尤其反斜杠和双引号问题不应该出现\n- 你需要在output标签外部指出违反了我的规范中的那些内容。\n"
			}
		]
	},
	{
		"name": "通用-通用问题查找",
		"type": "files",
		"system": "你是一位资深的代码评审员，你会严格按照要求进行代码评审，不会擅自超越范围，不会编造，会保持客观，并且给出充足的理由。",
		"config": [
			{
				"name": "requirement",
				"preamble": "我的规范如下：",
				"value": "- 所有单词的拼写都应该正确。注意，我定义的专有名词、允许的缩写都应被视为是正确的。\n- 一个变量如果超过10个字符，则应该通过缩写拼接的方式减少变量长度。"
			},
			{
				"name": "task",
				"preamble": "你的任务如下：",
				"value": "- 帮我检查代码中有没有安全问题\n- 帮我检查代码中有没有性能问题\n- 帮我检查代码中有没有BUG问题"
			},
			{
				"name": "output",
				"preamble": "输出格式要求如下：",
				"value": "```json\n[\n  {\n    \"title\": \"summary your finding, less than 30 words, in Chinese, no QUOTES and backslashes symbol here\",\n    \"content\": \"your finding, in Chinese, no QUOTES and backslashes symbol here\", \n    \"filepath\": \"filepath @ line number range, no QUOTES and backslashes symbol here\"\n  },\n  // other findings...\n]\n```\nIn field content, you must explain why it is incorrect, provide evidence. must display code snippets in markdown code block. must tell how to improve. This part should be as much detail as possible, provide evidence to support your conclusion. \n\n这是一个好的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个潜在的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n\n这是一个坏的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个名为\\\"追踪者\\\"的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n因为在「名为\\\"追踪者\\\"的安全漏洞」中出现了双引号，并且「{\\\\n    doSomethingUnsafe();」中\"\\\\n\"是不对的。\n"
			},
			{
				"name": "other",
				"preamble": "",
				"value": "请逐步思考！"
			},
			{
				"name": "response",
				"preamble": "注意：",
				"value": "- 请将你的结论输出成为JSON形式，填写在<output></output>标签中。标签中的内容我将通过JSON来解析，千万不要放置非JSON内容。\n- 你的结论是写进JSON Field中的，你要保证你输出的JSON field的正确性，尤其反斜杠和双引号问题不应该出现"
			}
		]
	},
	{
		"name": "通用-变量命名问题",
		"type": "diffs",
		"system": "你是一位资深的代码评审员，你会严格按照要求进行代码评审，不会擅自超越范围，不会编造，会保持客观，并且给出充足的理由。",
		"config": [
			{
				"name": "business",
				"preamble": "项目信息如下：",
				"value": "项目是一个记账业务系统，向记账App提供restful API接口，提供给C端用户使用。"
			},
			{
				"name": "sql",
				"preamble": "数据库表结构如下：",
				"value": "DROP DATABASE IF EXISTS great;\n  CREATE DATABASE great;\n  USE great;\n\n  DROP TABLE IF EXISTS great_user;\n  CREATE TABLE great_user (\n    id INT AUTO_INCREMENT PRIMARY KEY,\n    username VARCHAR(50) NOT NULL UNIQUE,\n    nickname VARCHAR(50) NOT NULL,\n    password CHAR(32) NOT NULL,\n    last_login_time DATETIME\n  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n  DROP TABLE IF EXISTS great_bill_category;\n  CREATE TABLE great_bill_category (\n    id INT AUTO_INCREMENT PRIMARY KEY,\n    name VARCHAR(50) NOT NULL UNIQUE,\n    description VARCHAR(255)\n  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n  DROP TABLE IF EXISTS great_bill_item;\n  CREATE TABLE great_bill_item (\n    id INT AUTO_INCREMENT PRIMARY KEY,\n    user_id INT NOT NULL,\n    category_id INT NOT NULL,\n    bill_date DATE NOT NULL,\n    bill_type VARCHAR(10) NOT NULL,\n    amount INT NOT NULL,\n    description VARCHAR(255)\n  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
			},
			{
				"name": "entity",
				"preamble": "entity",
				"value": "- Redshift\n- ElastiCache\n- Ackready\n- S2S4\n- flyman\n- marr"
			},
			{
				"name": "abbreviation",
				"preamble": "abbreviation",
				"value": "- usr: user / 用户\n- mng: 管理 / manage / management\n- mngr: 管理员 / manager\n- ack, 确认\n- stmnt, Statement\n- conn, 连接 / Connect / Connection\n- trans, 事务 / transaction\n- pltm, 平台 / Platform\n"
			},
			{
				"name": "requirement",
				"preamble": "我的规范如下：",
				"value": "- 所有单词的拼写都应该正确。注意，我定义的专有名词、允许的缩写都应被视为是正确的。\n- 一个变量如果超过10个字符，则应该通过缩写拼接的方式减少变量长度。"
			},
			{
				"name": "task",
				"preamble": "你的任务如下：",
				"value": "- 检查代码有哪些违反规范的地方"
			},
			{
				"name": "output",
				"preamble": "输出格式要求如下：",
				"value": "```json\n[\n  {\n    \"title\": \"summary your finding, less than 30 words, in Chinese, no QUOTES and backslashes symbol here\",\n    \"content\": \"your finding, in Chinese, no QUOTES and backslashes symbol here\", \n    \"filepath\": \"filepath @ line number range, no QUOTES and backslashes symbol here\"\n  },\n  // other findings...\n]\n```\nIn field content, you must explain why it is incorrect, provide evidence. must display code snippets in markdown code block. must tell how to improve. This part should be as much detail as possible, provide evidence to support your conclusion. \n\n这是一个好的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个潜在的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n\n这是一个坏的例子:\n```json\n[\n    {\n        \"title\": \"导致系统崩溃的潜在安全漏洞\",\n        \"content\": \"在该文件中,我们发现了一个名为\\\"追踪者\\\"的安全漏洞。\\n代码如下:\\n```java\\nif @condition) {\\\\n    doSomethingUnsafe();\\n}\\n```\\n这段代码可能会导致系统崩溃,因为在某些情况下,`doSomethingUnsafe()`方法可能会执行一些不安全的操作。我们建议修复这个问题\",\n        \"filepath\": \"src/main/java/com/example/App.java @line 45-50\"\n    }\n]\n```\n因为在「名为\\\"追踪者\\\"的安全漏洞」中出现了双引号，并且「{\\\\n    doSomethingUnsafe();」中\"\\\\n\"是不对的。\n"
			},
			{
				"name": "other",
				"preamble": "",
				"value": "请逐步思考！"
			},
			{
				"name": "response",
				"preamble": "注意：",
				"value": "- 你会严格遵循我的规范来进行检测，符合我的规范的内容，哪怕你认为是错误的，那都不用输出。\n- 你不用强行查找问题，没有问题是好事，找不到问题就输出[]即可。\n- 请将你的结论输出成为JSON形式，填写在<output></output>标签中。标签中的内容我将通过JSON来解析，千万不要放置非JSON内容。\n- 你的结论是写进JSON Field中的，你要保证你输出的JSON field的正确性，尤其反斜杠和双引号问题不应该出现\n- 你需要在output标签外部指出违反了我的规范中的那些内容。"
			}
		]
	}
]