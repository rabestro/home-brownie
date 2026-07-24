# 🧞 Home Genie

Welcome to the documentation for **Home Genie** — an autonomous, AI-powered Telegram assistant designed for homelabs and personal smart home environments.

Powered by the **Google Antigravity SDK** and **Gemini 3.1 Flash**, Home Genie coordinates multiple Model Context Protocol (MCP) servers to manage household documents, knowledge wikis, smart home devices, and network infrastructure directly from Telegram text and voice messages.

---

## ✨ Key Capabilities

- 🏛 **Paperless-ngx**: Search document archives, auto-assign metadata and tags, upload new documents.
- 📚 **GitHub Wiki (Quartz)**: Look up family notes, create and update Markdown documentation in `my-family-wiki`.
- 🏠 **Home Assistant**: Query smart sensors, lights, climate control, and trigger automations.
- ☁️ **Cloudflare**: Inspect DNS records, Cloudflare Tunnels, and Zero Trust access policies.
- 🔌 **Home Connect**: Query and control smart household appliances (Bosch, Siemens, Gaggenau).
- 🔒 **Multi-Tenant Family RBAC**: Per-user permission mapping. MCP servers are dynamically included or excluded per Telegram User ID based on assigned API tokens.

---

## 🚀 Quick Navigation

- [Quickstart Guide](setup/quickstart.md)
- [Environment & RBAC Configuration](setup/configuration.md)
- [Docker Deployment](setup/docker.md)
- [Architecture Overview](architecture.md)
