#!/usr/bin/env python3
import streamlit as st
import os
from llama_stack_client import LlamaStackClient, Agent
from llama_stack.apis.common.content_types import URL

MODEL_SERVICE_URL = f"{os.getenv('MODEL_SERVICE_URL', 'http://localhost:8001')}"
MODEL_SERVICE_API_KEY = os.getenv("MODEL_SERVICE_API_KEY")


class ToolManager:
    def __init__(
        self,
        server_url: "str" = MODEL_SERVICE_URL,
        api_key: "str" = MODEL_SERVICE_API_KEY,
    ) -> "None":
        self.server_url = server_url
        self.api_key = api_key
        self.client = None
        self.agent = None
        self.model_identifier = None
        self.session_id = None
        self.custom_tools = {}
        self.mcp_servers = {}

    def connect(self) -> "tuple[bool, str]":
        """
        connects to a given llama-stack server
        """
        try:
            self.client = LlamaStackClient(
                base_url=self.server_url, api_key=self.api_key
            )
            identifier = self.client.models.list()[0].identifier

            available_toolgroups = []
            try:
                toolgroups = self.client.toolgroups.list()
                available_toolgroups = [tg.identifier for tg in toolgroups]
            except:
                # if no toolgroups are registered, continue with empty list
                pass

            self.agent = Agent(
                self.client,
                model=identifier,
                instructions="You are a helpful assistant with access to tools.",
                tools=available_toolgroups,
            )

            self.session_id = self.agent.create_session("tool_session")
            return True, "Connected"
        except Exception as err:
            return False, str(err)

    def chat(self, message: "str") -> "str":
        """
        sends message to an Agent instance
        """
        if not self.agent:
            success, msg = self.connect()
            if not success:
                return f"Connection failed: {msg}"

        try:
            response = self.agent.create_turn(
                session_id=self.session_id,
                messages=[{"role": "user", "content": message}],
                stream=False,
            )
            return response.output_message.content
        except Exception as err:
            return f"Error: {str(err)}"

    def get_available_tools(self) -> "None":
        """
        lists available tools
        """
        builtin_tools = [
            "builtin::code_interpreter",
            "builtin::websearch",
            "builtin::wolfram_alpha",
        ]
        custom_tool_names = [f"custom::{name}" for name in self.custom_tools.keys()]
        mcp_tool_names = [f"mcp::{name}" for name in self.mcp_servers.keys()]

        return builtin_tools + custom_tool_names + mcp_tool_names

    def get_registered_toolgroups(self) -> "list[tuple[str, str]]":
        """
        gets all registered toolgroups from the Llama Stack server
        """
        if not self.client:
            return []

        try:
            toolgroups = self.client.toolgroups.list()
            return [(tg.identifier, tg.provider_id) for tg in toolgroups]
        except Exception:
            return []

    def register_tool(
        self, name: "str", description: "str", code: "str"
    ) -> "tuple[bool, str]":
        """
        registers a new custom tool
        """
        try:
            self.custom_tools[name] = {
                "description": description,
                "code": code,
                "function": None,
            }
            return True, "Tool Registered"
        except Exception as err:
            return False, str(err)

    def register_mcp_server(
        self, name: "str", endpoint_url: "str", description="", auth_token=""
    ) -> "tuple[bool, str]":
        """
        registers a new MCP server as a toolgroup
        """
        if not self.client:
            return False, "Not connected to Llama Stack"

        try:
            toolgroup_id = f"mcp::{name}"

            provider_data = (
                {"Authorization": f"Bearer {auth_token}"} if auth_token else None
            )

            self.client.toolgroups.register(
                toolgroup_id=toolgroup_id,
                provider_id="model-context-protocol",
                mcp_endpoint=URL(uri=endpoint_url),
                extra_headers=provider_data,
            )

            self.mcp_servers[name] = {
                "endpoint_url": endpoint_url,
                "description": description,
                "toolgroup_id": toolgroup_id,
            }
            self.connect()

            return True, f"MCP server '{name}' registered successfully"
        except Exception as err:
            return False, f"Failed to register MCP server: {str(err)}"

    def unregister_mcp_server(self, name: "str") -> "tuple[bool, str]":
        """
        unregisters an MCP server
        """
        if not self.client:
            return False, "Not connected to Llama Stack"

        try:
            toolgroup_id = f"mcp::{name}"
            self.client.toolgroups.unregister(toolgroup_id=toolgroup_id)

            if name in self.mcp_servers:
                del self.mcp_servers[name]

            self.connect()

            return True, f"MCP server '{name}' unregistered successfully"
        except Exception as err:
            return False, f"Failed to unregister MCP server: {str(err)}"


def main() -> "None":
    if "tool_manager" not in st.session_state:
        st.session_state.tool_manager = ToolManager()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "connected" not in st.session_state:
        st.session_state.connected = False

    tool_manager = st.session_state.tool_manager
    st.title("🛠️ Llama Stack Tool & MCP Manager")

    with st.sidebar:
        st.header("🔌 Connection")

        success, msg = tool_manager.connect()
        st.session_state.connected = success

        if st.session_state.connected:
            st.success("✅ Connected")
        else:
            st.error("❌ Not connected")
            st.info("Start server: `llama stack run`")

        st.header("🛠️ Available Tools")
        tools = tool_manager.get_available_tools()
        for tool in tools:
            st.write(f"• {tool}")

        if st.session_state.connected:
            st.subheader("📋 Registered Toolgroups")
            toolgroups = tool_manager.get_registered_toolgroups()
            if toolgroups:
                for tg_id, provider_id in toolgroups:
                    st.write(f"• {tg_id} ({provider_id})")
            else:
                st.write("No toolgroups registered")

        tab1, tab2 = st.tabs(["➕ Custom Tool", "🌐 MCP Server"])

        with tab1:
            st.subheader("Register Custom Tool")
            with st.form("new_tool"):
                tool_name = st.text_input("Tool Name")
                tool_description = st.text_area("Description")
                tool_code = st.text_area("Python Code", height=150)

                if st.form_submit_button("Register Tool"):
                    if tool_name and tool_description and tool_code:
                        success, message = tool_manager.register_tool(
                            tool_name, tool_description, tool_code
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("All fields required")

        with tab2:
            st.subheader("Register MCP Server")
            with st.form("new_mcp_server"):
                mcp_name = st.text_input("MCP Server Name")
                mcp_auth_token = st.text_input("Auth Token (Optional)", type="password")

                mcp_endpoint = st.text_input(
                    "Endpoint URL", placeholder="http://localhost:8000/sse"
                )
                mcp_description = st.text_area("Description (optional)")

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Register MCP Server"):
                        if mcp_name and mcp_endpoint:
                            if st.session_state.connected:
                                success, message = tool_manager.register_mcp_server(
                                    mcp_name,
                                    mcp_endpoint,
                                    mcp_description,
                                    mcp_auth_token,
                                )

                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                st.error("Please connect to Llama Stack first")
                        else:
                            st.error("Name and endpoint URL required")

                with col2:
                    if st.form_submit_button("Unregister"):
                        if mcp_name:
                            if st.session_state.connected:
                                success, message = tool_manager.unregister_mcp_server(
                                    mcp_name
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                st.error("Please connect to Llama Stack first")
                        else:
                            st.error("Name required for unregistration")

    col1, col2 = st.columns([16, 9])

    with col1:
        st.header("💬 Chat")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        if prompt := st.chat_input("Ask me anything..."):
            if not st.session_state.connected:
                st.error("Please connect to llama-stack first")
            else:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = tool_manager.chat(prompt)
                    st.write(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )

    with col2:
        st.header("🔧 Tool Details")

        if tool_manager.custom_tools:
            st.subheader("Custom Tools")
            for name, details in tool_manager.custom_tools.items():
                with st.expander(f"📋 {name}"):
                    st.write("**Description:**")
                    st.write(details["description"])
                    st.write("**Code:**")
                    st.code(details["code"], language="python")

        if tool_manager.mcp_servers:
            st.subheader("MCP Servers")
            for name, details in tool_manager.mcp_servers.items():
                with st.expander(f"🌐 {name}"):
                    st.write("**Endpoint:**")
                    st.code(details["endpoint_url"])
                    st.write("**Toolgroup ID:**")
                    st.code(details["toolgroup_id"])
                    if details["description"]:
                        st.write("**Description:**")
                        st.write(details["description"])

        if not tool_manager.custom_tools and not tool_manager.mcp_servers:
            st.info("No custom tools or MCP servers registered yet")

        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
