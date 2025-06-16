# Llama Stack Example Agent Application

## Application Information

The application created by this AI Software Template uses an existing `llama-stack-agent` service and creates a `streamlit` application around it.

This application relies on [Meta's python llama-stack package](https://github.com/meta-llama/llama-stack) to simplify communication with the Model Service and uses [Streamlit](https://streamlit.io/) for the UI layer. This Chatbot takes conversational input from a user. Based on the input and data from previous conversations, the Chatbot formulates an appropriate response to the prompt.

## Prerequisites

Before deploying this application, a secret, `llama-stack-secret` must exist in the same namespace, with the following key-value pairs:

- `OLLAMA_URL`: The hostname of the Ollama instance
- `OLLAMA_API_TOKEN`: An API key used to access the Ollama instance (if needed)
