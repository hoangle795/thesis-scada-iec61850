# ============================================================
# Infrastructure as Code - Trạm Biến Áp Kỹ Thuật Số
# Quản lý phân vùng mạng OT/IT theo QĐ 1603/QĐ-EVN
# ============================================================

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# ── Mạng OT: Station Bus (IEC 61850) ─────────────────────
resource "docker_network" "substation_net" {
  name   = "substation-net"
  driver = "bridge"
  ipam_config {
    subnet  = "172.20.0.0/24"
    gateway = "172.20.0.1"
  }
}

# ── Mạng IT: Dispatch/Control Center ─────────────────────
resource "docker_network" "it_net" {
  name   = "it-net"
  driver = "bridge"
  ipam_config {
    subnet  = "172.21.0.0/24"
    gateway = "172.21.0.1"
  }
}

# ── Output thông tin sau khi tạo ──────────────────────────
output "ot_network_id" {
  description = "ID của mạng OT (substation-net)"
  value       = docker_network.substation_net.id
}

output "it_network_id" {
  description = "ID của mạng IT (it-net)"
  value       = docker_network.it_net.id
}

output "network_summary" {
  description = "Tóm tắt phân vùng mạng"
  value = {
    OT_network = "172.20.0.0/24 — IED, SCADA, HMI, Grafana, Gateway"
    IT_network = "172.21.0.0/24 — Gateway (DMZ), Dispatch Center"
    DMZ_node   = "Gateway kết nối cả 2 mạng tại 172.20.0.30 và 172.21.0.30"
  }
}
