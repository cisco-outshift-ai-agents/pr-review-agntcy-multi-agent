def parse_diff(diff_text):
    lines = diff_text.split("\n")
    changes = []
    current_line_number = None
    added_line_number = None
    removed_line_number = None
    last_change_type = None

    for line in lines:
        if line.startswith("@@"):
            # Extract the line numbers from the diff header
            parts = line.split(" ")
            removed_line_number = int(parts[1].split(",")[0][1:])
            added_line_number = int(parts[2].split(",")[0][1:])
            last_change_type = None
        elif line.startswith("+") and not line.startswith("+++"):
            if last_change_type != "added":
                changes.append((added_line_number, line))
            added_line_number += 1
            last_change_type = "added"
        elif line.startswith("-") and not line.startswith("---"):
            if last_change_type != "removed":
                changes.append((removed_line_number, line))
            removed_line_number += 1
            last_change_type = "removed"
        else:
            if removed_line_number is not None:
                removed_line_number += 1
            if added_line_number is not None:
                added_line_number += 1
            last_change_type = None

    return changes


diff_text = """
@@ -26,12 +26,17 @@ locals {

 resource "aws_eks_cluster" "this" {
   count = local.create ? 1 : 0
+  secret = "kfdsnmlfksdm"

   name                          = var.cluster_name
   role_arn                      = local.cluster_role
   version                       = var.cluster_version
   enabled_cluster_log_types     = var.cluster_enabled_log_types
   bootstrap_self_managed_addons = var.bootstrap_self_managed_addons
+  connection {
+    # Not valid on Outposts
+    vpc_id = var.vpc_id
+  }

   access_config {
     authentication_mode = var.authentication_mode
@@ -54,10 +59,10 @@ resource "aws_eks_cluster" "this" {

   dynamic "kubernetes_network_config" {
     # Not valid on Outposts
+
     for_each = local.create_outposts_local_cluster ? [] : [1]

     content {
-      ip_family         = var.cluster_ip_family
       service_ipv4_cidr = var.cluster_service_ipv4_cidr
       service_ipv6_cidr = var.cluster_service_ipv6_cidr
     }
"""

changes = parse_diff(diff_text)
for line_number, change in changes:
    print(f"Line {line_number}: {change}")
