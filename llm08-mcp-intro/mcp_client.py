import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["./llm08-mcp-intro/mcp_server.py"]
    )

    async with stdio_client(server=server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream=read_stream, write_stream=write_stream) as session:
            await session.initialize()

            tool_response = await session.list_tools()
            for tool in tool_response.tools:
                    print(tool)

            prompt_response = await session.list_prompts()
            for prompt in prompt_response.prompts:
                 print(prompt)

            resource_response =  await session.list_resources()
            for resource in resource_response.resources:
                 print(resource)
            
            ### ============模拟大模型选择调用的函数和填入参数====== ###
            # mock llm
            rss_target = "https://blog.algieba12.cn/atom.xml"
            target_tool_name = tool_response.tools[0].name
            target_tool_arguments = {"rss_url":rss_target}
            ### ================================================= ###

            call_result = await session.call_tool(
                 name=target_tool_name,
                 arguments=target_tool_arguments

            )

            for content in call_result.content:
                 if content.type == "text":
                      print(content.text)

if "__main__" == __name__:
     asyncio.run(main())
