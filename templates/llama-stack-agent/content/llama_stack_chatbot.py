#!/usr/bin/env python3
import streamlit as st
import os
from llama_stack_client import LlamaStackClient, Agent

MODEL_SERVICE_URL = f"{os.getenv('MODEL_SERVICE_URL', 'http://localhost:8001')}"
MODEL_SERVICE_API_KEY = os.getenv("MODEL_SERVICE_API_KEY")


class ToolManager:
    def __init__(
        self,
        server_url: "str" = MODEL_SERVICE_URL,
    ) -> "None":
        self.server_url = server_url
        self.client = None
        self.agent = None
        self.model_identifier = None
        self.session_id = None
        self.custom_tools = {}

    def connect(self) -> "tuple[bool, str]":
        """
        connects to a given llama-stack server
        """
        try:
            self.client = LlamaStackClient(base_url=self.server_url)
            identifier = self.client.models.list()[0].identifier

            self.agent = Agent(
                self.client,
                model=identifier,
                instructions="You are a helpful assistant with access to tools.",
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
            self.connect()

        response = self.agent.create_turn(
            session_id=self.session_id,
            messages=[{"role": "user", "content": message}],
            stream=False,
        )
        return response.output_message.content

    def get_available_tools(self):
        """
        lists available tools.
        """
        builtin_tools = [
            "builtin::code_interpreter",
            "builtin::websearch",
            "builtin::wolfram_alpha",
        ]
        custom_tool_names = [f"custom::{name}" for name in self.custom_tools.keys()]

        return builtin_tools + custom_tool_names

    def register_tool(self, name, description, code):
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


def main() -> "None":
    if "tool_manager" not in st.session_state:
        st.session_state.tool_manager = ToolManager()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "connected" not in st.session_state:
        st.session_state.connected = False

    tool_manager = st.session_state.tool_manager
    st.title("🛠️ Llama Stack Example Template")

    with st.sidebar:
        st.header("🔌 Connection")

        st.session_state.connected = tool_manager.connect()

        if st.session_state.connected:
            st.success("✅ Connected")
        else:
            st.error("❌ Not connected")
            st.info("Start server: `llama stack run`")

        st.header("🛠️ Available Tools")
        tools = tool_manager.get_available_tools()
        for tool in tools:
            st.write(f"• {tool}")

        st.header("➕ Register New Tool")
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
        else:
            st.info("No custom tools registered yet")

        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
