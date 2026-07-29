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

## ⚠️ Hardware Requirements & CPU Compatibility

**Home Brownie** uses the **Google Antigravity SDK** (`google-antigravity`), which embeds native Go binaries compiled with modern CPU instruction set requirements:

- **x86_64 / amd64**: Requires **AVX** instruction support (Intel Haswell / 4th Gen 2013+ or AMD FX-8300+).
  - ❌ *Not supported*: Older x86_64 CPUs and many NAS devices (Intel Celeron J3455/J4125, Atom) lacking AVX instructions (`FATAL ERROR: This binary was compiled with avx enabled...`).
- **ARM64 / aarch64**: Requires **ARM Cryptography Extensions (AES)**.
  - ❌ *Not supported*: **Raspberry Pi 3** and **Raspberry Pi 4** (Broadcom BCM2837 and BCM2711 lack hardware AES instructions). Crashes with `FATAL ERROR: This binary was compiled with aes enabled...`.
  - ✅ *Supported*: **Raspberry Pi 5** (Broadcom BCM2712 / Cortex-A76), Apple Silicon, and modern ARM64 cloud VPS.

---

## 🚀 Quick Navigation

- [Quickstart Guide](setup/quickstart.md)
- [Environment & RBAC Configuration](setup/configuration.md)
- [Docker Deployment](setup/docker.md)
- [Architecture Overview](architecture.md)
