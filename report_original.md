# 成都东软学院

实 验 报 告

> 课程名称： [人工智能提示工程]{.underline}
>
> 指导教师： [谢心]{.underline}
>
> 学 院： [数智应用技术学院]{.underline}
>
> 年级专业： [24级软件工程]{.underline}
>
> 班 级： [24402]{.underline}
>
> 学 号： [24068240217]{.underline}
>
> 姓 名： [陶俊辉]{.underline}

# 实验（1）基于 AnythingLLM 的 Agent 知识库查询功能开发

**【实验目的】**

1.  掌握 AnythingLLM 本地服务的部署与 API Key、工作区 Slug 的获取方法。

2.  开发anythingllm_query工具函数，实现通过 API 调用 AnythingLLM 聊天接口。

3.  修改现有chat_client.py代码，添加工具调用逻辑，实现用户提及 "文档仓库 / 文件仓库 / 仓库" 时自动触发知识库查询。

4.  完成功能测试与文档更新，确保功能稳定可用。

**【实验内容】**

**2.1实验过程：**

(1) 开启AnythingLLM的本地服务。创建API KEY。在新建的工作区的设置页面找到向量数据库的STLYG ID。在，env文件和env.example文件新增ANYTHINGLLM_API_KEY、ANYTHINGLLM_WORKSPACE_SLUG变量。在.env文件中填写 ANYTHINGLM_API_KEY、ANYTHINGLLM_WORKSPACE_SLUG的正确信息。

![图 1 获取Anything APIkey](media/image1.png){width="5.768055555555556in" height="1.0138888888888888in"}

![图 2 获取向量数据库标识符](media/image2.png){width="5.768055555555556in" height="3.370138888888889in"}

![图 3 修改 env文件](media/image3.png){width="5.768055555555556in" height="3.0861111111111112in"}

(2) 输入提示词：

提示词：

1.理解这个Agent开发教学项目。

> 2.创建practice4目录，复制practice03中的代码，实现下面的新功能：

开发anythinglmguery.fnction:

-使用subprocess模块调用cur命令，访问http：//localhost：3001/api/v1/workspace/{workspace_slug}/chat的聊天API

接口访问AnythingLLM的数据，注意中文编码的问题

-使用message 字段发送查询

－使用API密钥进行认证

-在env文件中读取ANYTHINGLLM_API_KEY、ANYTHINGLLM_WORKSPACE_SLUG变量

-如果遇到错误，认真阅读 \`http://locathost:3001/api/docs/的文档

-进行测试

3.修改chat_client.py：

-添加新的anythingllm_guery工具定义和function call调用，更新系统可用function列表

-更新系统提示词，明确当用户提到"文档仓库"、"文件仓库"、"仓库"时触发anythinglLm_query工具

4.测试代码，确保能够正常运行

5.更新README.md,说明了如何使用新功能

![图 4 提交提示词](media/image4.png){width="4.156829615048119in" height="8.001116579177603in"}

**2.2实验结果：**

**成功运行。**

![图 5 模型回答](media/image5.png){width="5.500767716535433in" height="6.3029625984251965in"}

**【实验总结】**

本次实验核心目标是开发一个能够与本地知识库交互的智能代理，在这个实验过程中成功在我的电脑上部署乐AnythingLLM服务，创建了APIKey，并将该APIKey和WORKSPACE_SLUG配置到项目的.env文件中，同时在practice03目录中的代码基础上，在practice04目录中添加了anythingllm_query工具函数，通过使用Python的subprocess模块，通过构造curl命令来调用AnythingLLM的聊天接口，成功实现通过命令行与大模型对话了解工作区中的文档信息，该项目通过动手实践，将课程中学习的Agent、工具调用、API集成等知识点串联起来，为我以后从事更复杂的智能体开发或AI应用工程化打下了坚实的基础。
