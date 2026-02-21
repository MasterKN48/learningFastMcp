# Learning Model Context Protocol (MCP) & FastMCP: Expense Tracker

This project is a dedicated learning workspace for mastering the **Model Context Protocol (MCP)** and building a production-ready **Expense Tracker MCP Server** using **FastMCP**.

## 🚀 Quick Start (Setup with `uv`)

This project uses `uv` for lightning-fast Python package management and `FastMCP` (v3.0+) for building powerful MCP servers.

```bash
# Initialize the project
uv init .

# Add FastMCP
uv add fastmcp

# --- New Quick Scripts ---
# Run the main SQLite server
uv run start

# Launch the MCP Inspector for debugging
uv run inspect

# Run the legacy JSON server
uv run server
```

---

## 📚 MCP: Deep Dive Documentation

### 1. History & Evolution

- **November 2024:** Introduced by **Anthropic** as an open standard to solve the **"N×M" integration problem** (where every data source needed a custom connector for every LLM).
- **Rapid Adoption:** Quickly supported by major AI players including **OpenAI**, **Google DeepMind**, and developer tools like **Cursor**.
- **December 2025:** Anthropic donated MCP to the **Agentic AI Foundation (AAIF)** under the Linux Foundation to ensure community-driven, vendor-neutral growth.

### 2. Core Architecture

MCP follows a modular triplet design:

- **MCP Host:** The runtime environment (e.g., Claude Desktop, Cursor, IDEs) where the LLM lives.
- **MCP Client:** The bridge inside the Host that negotiates with servers.
- **MCP Server:** The specialized service that provides **Tools**, **Resources**, and **Prompts**.

#### The Three Layers:

1.  **Data Layer:** High-level primitives like Tools (actions), Resources (data), and Prompts (templates).
2.  **Protocol Layer:** Lifecycle management (handshake, pings) and message framing based on JSON-RPC 2.0.
3.  **Transport Layer:** The physical communication channel.
    - **Stdio:** Best for local desktop apps (child processes).
    - **SSE (Server-Sent Events):** Best for remote/networked servers via HTTP.

---

## 🛰️ Technical Protocol Details

### 1. JSON-RPC 2.0 Message Structure

MCP communication relies on three message types:

| Type             | Structure                                                       | Expects Response? |
| :--------------- | :-------------------------------------------------------------- | :---------------- |
| **Request**      | `{"jsonrpc": "2.0", "id": 1, "method": "...", "params": {...}}` | **Yes**           |
| **Response**     | `{"jsonrpc": "2.0", "id": 1, "result": {...}}`                  | **No**            |
| **Notification** | `{"jsonrpc": "2.0", "method": "...", "params": {...}}`          | **No**            |

### 2. Error Handling & Codes

MCP uses standard JSON-RPC codes plus protocol-specific extensions:

- `-32700`: Parse Error (Invalid JSON).
- `-32600`: Invalid Request.
- `-32601`: Method Not Found.
- `-32000`: Server Error (General).
- **MCP Specific:**
  - `-32800`: **Request Cancelled** (Client or server aborted).
  - `-32801`: **Content Too Large** (Payload exceeds transport limits).

### 3. Connection Health (Ping)

Either side can send a `ping` request to verify the connection is alive.

```json
// Request
{"jsonrpc": "2.0", "id": "p1", "method": "ping"}
// Response
{"jsonrpc": "2.0", "id": "p1", "result": {}}
```

### 3. Lifecycle & Handshakes

MCP is a stateful protocol. A connection follows a strict lifecycle:

1.  **Initialize Request:** Client sends its protocol version and capabilities.
2.  **Initialize Response:** Server replies with its version, capabilities, and basic info.
3.  **Initialized Notification:** Client confirms it's ready to start.
4.  **Operational Phase:** Standard tool calls and resource requests.
5.  **Shutdown:** Graceful termination of the session.

### 4. JSON-RPC 2.0 Implementation

All MCP communication happens over JSON-RPC 2.0. This ensures a language-agnostic, predictable messaging format.

- **Requests:** Require an `id` and expect a reply.
- **Responses:** Match the `id` and contain `result` or `error`.
- **Notifications:** "Fire and forget" messages without an `id`.

---

## 🛠️ Advanced Capabilities & Features

### 1. Client Capabilities

Clients (Hosts like Claude Desktop or Cursor) can offer specialized features to servers:

- **Roots:** Defining the workspace "safe zones" (URIs/Paths) the server is allowed to access.
- **Sampling:** Allowing the server to ask the LLM for completions via the client (agentic behavior).
- **Experimental:** Negotiating non-standard features or future protocol extensions.

### 2. Message Exchange Flow

How a user request traverses the system:

1.  **User** sends a prompt to the **Host** (e.g., "Add $10 for lunch to my tracker").
2.  **Host** parses the intent and checks available **Server** tools.
3.  **Host** sends a `tools/call` request to the **MCP Server** via JSON-RPC.
4.  **Server** executes `add_expense(amount=10, ...)` and returns a `result`.
5.  **Host** receives the result and provides a final natural language response to the **User**.

### 2. Server Capabilities

Servers declare what primitives they support during initialization:

- **Resources:** `listChanged: true` (Can notify when data sources change) & `subscribe` support.
- **Tools:** `listChanged: true` (Can notify when functions are added/removed).
- **Prompts:** Template-based triggers.
- **Logging:** Capability to stream server-side logs to the client for debugging (`notifications/logging`).

### 3. Elicitation (Client Information Requests)

Elicitation allows a server to proactively ask the user for missing information via the client.

- **Form Mode:** Requests structured data (e.g., "What is the budget category?") using JSON Schema validation.
- **URL Mode:** Directs the user to an external URL (e.g., for OAuth or payment) so sensitive credentials never touch the MCP client/server directly.

### 3. Dynamic Messaging (ListChanged, Subscribe, Notify)

- **`listChanged` Notification:** Sent by server to client when its tool/resource list updates.
- **`resources/subscribe` Request:** Client asks to be notified of any changes to a specific resource URI.
- **`notifications/message`:** General purpose asynchronous messages for streaming or status updates.

### 4. Connection Termination

- **Shutdown:** Orderly request to stop the session.
- **Exit:** Notification sent after shutdown to terminate the process/transport.

---

## 🛠 SDK vs. FastMCP vs. FastMCP2/3

| Feature        | Official MCP SDK (Python)         | FastMCP (High-Level)             | FastMCP 3.0 (Latest)               |
| :------------- | :-------------------------------- | :------------------------------- | :--------------------------------- |
| **Philosophy** | Low-level, granular, verbose.     | Pythonic, decorator-based, fast. | Component-based, enterprise-ready. |
| **Setup**      | Requires significant boilerplate. | One-line tool creation.          | Modular Architecture.              |
| **Tools**      | Manual registration via classes.  | `@mcp.tool()` decorator.         | Advanced context & logging.        |
| **Evolution**  | Stable foundation.                | Standalone production framework. | Added Versioning & OpenTelemetry.  |

---

## 🛠️ Developer Tools

### 1. MCP Inspector

The **MCP Inspector** is the "Postman for MCP". It is an interactive, browser-based tool for testing servers.

- **Launch:** `npx @modelcontextprotocol/inspector <command-to-run-server>`
- **Features:**
  - Visualizes all available Tools, Resources, and Prompts.
  - Manually trigger tool calls with custom JSON parameters.
  - Real-time monitoring of JSON-RPC traffic and server logs.
  - Supports Stdio, SSE, and HTTP transports.

### 2. Standardized Server Logging

Servers can send asynchronous logs to the client using `notifications/logging`.

- **Severity Levels:** `debug`, `info`, `warn`, `error`.
- **Structure:** Includes a logger name and arbitrary serializable data for rich, queryable logs in the Host interface.

### Why FastMCP?

While the official SDK is great for foundational work, **FastMCP** abstracts away the complexity of JSON-RPC handling, transport management, and type validation. It allows you to build a production-ready server in minutes rather than hours.

---

## 📈 Learning Progress

- [x] Project initialized with `uv`.
- [x] FastMCP installed (v3.0.x).
- [x] Core technical research completed (History, Layering, JSON-RPC, Elicitation).
- [x] **Implementation phase: Expense Tracker Server**
  - [x] Create `add_expense` tool with validation and `Context` logging.
  - [x] Implement SQLite-based persistent storage (id, amount, date, category, subcategory, note).
  - [x] Add summary and listing tools (Resource & Tool).
  - [x] Implement Categories and Subcategories resources from JSON.
  - [ ] Explore custom Resource Providers for external data.
  - [ ] Explore SSE transport deployments.

---

_Last updated: 2026-02-21_
