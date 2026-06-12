#!/usr/bin/env node
/**
 * gpu-rental-mcp
 * MCP Server for comparing and renting cheap vGPUs via Shadeform.
 * Covers 30+ cloud providers (Lambda, RunPod, Vast, CoreWeave, Nebius, …)
 * with a single API key.
 *
 * Tools:
 *   list_cheapest_gpus     – compare prices across all providers, sorted cheapest first
 *   filter_by_gpu_type     – search for a specific GPU model
 *   rent_instance          – launch a GPU instance (⚠️ spends money)
 *   list_my_instances      – show all your active instances
 *   get_instance_info      – get full details of one instance
 *   stop_instance          – delete/terminate an instance (⚠️ destructive)
 *
 * Config (env vars):
 *   SHADEFORM_API_KEY   – required
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { ShadeformClient, NormalizedOffer } from "./shadeform.js";

// ─── Init ─────────────────────────────────────────────────────────────────────

const API_KEY = process.env.SHADEFORM_API_KEY;
if (!API_KEY) {
  process.stderr.write(
    "ERROR: SHADEFORM_API_KEY environment variable is not set.\n" +
    "Get your key at https://platform.shadeform.ai\n"
  );
  process.exit(1);
}

const client = new ShadeformClient(API_KEY);

const server = new McpServer({
  name: "gpu-rental-mcp",
  version: "1.0.0",
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatOfferTable(offers: NormalizedOffer[]): string {
  if (offers.length === 0) return "No offers found matching your criteria.";

  const lines: string[] = [
    `Found ${offers.length} offer(s) — sorted by price (cheapest first):\n`,
  ];

  for (let i = 0; i < offers.length; i++) {
    const o = offers[i];
    const status = o.available ? "✅ Available" : "❌ Unavailable";
    lines.push(
      `${i + 1}. ${o.gpu_type} × ${o.num_gpus} — ${o.cloud} / ${o.region}`,
      `   Type:       ${o.shade_instance_type} (${o.cloud_instance_type})`,
      `   Price:      $${o.price_per_hour_usd.toFixed(3)}/hr total` +
        (o.num_gpus > 1 ? ` ($${o.price_per_gpu_hour_usd.toFixed(4)}/GPU/hr)` : ""),
      `   VRAM:       ${o.vram_per_gpu_gb} GB/GPU → ${o.total_vram_gb} GB total`,
      `   RAM:        ${o.ram_gb} GB  |  vCPUs: ${o.vcpus}  |  Storage: ${o.storage_gb} GB`,
      `   Interconn.: ${o.interconnect}`,
      `   Status:     ${status}`,
      ""
    );
  }

  lines.push(
    "─────────────────────────────────────────",
    "To rent: use rent_instance with cloud, region, and shade_instance_type from above."
  );

  return lines.join("\n");
}

function formatInstance(inst: {
  id: string;
  cloud: string;
  region: string;
  shade_instance_type: string;
  name: string;
  status: string;
  status_details?: string;
  ip: string;
  ssh_user: string;
  ssh_port: number;
  cost_estimate: string;
  hourly_price?: number;
  configuration: {
    gpu_type: string;
    num_gpus: number;
    vram_per_gpu_in_gb: number;
    memory_in_gb: number;
    vcpus: number;
    storage_in_gb: number;
  };
  created_at: string;
  active_at?: string;
}): string {
  const hourly = inst.hourly_price ? `$${(inst.hourly_price / 100).toFixed(3)}/hr` : "N/A";
  const ssh = inst.ip
    ? `ssh ${inst.ssh_user}@${inst.ip} -p ${inst.ssh_port}`
    : "Not yet assigned";

  return [
    `Instance: ${inst.name} (${inst.id})`,
    `Cloud:    ${inst.cloud} / ${inst.region}`,
    `Type:     ${inst.shade_instance_type}`,
    `GPU:      ${inst.configuration.gpu_type} × ${inst.configuration.num_gpus} (${inst.configuration.vram_per_gpu_in_gb} GB VRAM each)`,
    `RAM:      ${inst.configuration.memory_in_gb} GB  |  vCPUs: ${inst.configuration.vcpus}  |  Storage: ${inst.configuration.storage_in_gb} GB`,
    `Status:   ${inst.status}${inst.status_details ? ` (${inst.status_details})` : ""}`,
    `Price:    ${hourly}  |  Total spent: $${inst.cost_estimate}`,
    `SSH:      ${ssh}`,
    `Created:  ${inst.created_at}`,
    inst.active_at ? `Active:   ${inst.active_at}` : "",
  ].filter(Boolean).join("\n");
}

// ─── Tool: list_cheapest_gpus ─────────────────────────────────────────────────

server.tool(
  "list_cheapest_gpus",
  "List the cheapest available GPU instances across 30+ cloud providers via Shadeform. " +
  "Returns offers sorted by price, normalized to USD per hour. " +
  "This is a read-only operation — no money is spent.",
  {
    limit: z.number().int().min(1).max(50).default(10)
      .describe("Maximum number of results to show (default: 10)"),
    only_available: z.boolean().default(true)
      .describe("Only show instances that are currently available (default: true)"),
    max_price_usd: z.number().positive().optional()
      .describe("Maximum price per hour in USD (e.g. 2.50)"),
    min_vram_gb: z.number().int().positive().optional()
      .describe("Minimum VRAM per GPU in GB (e.g. 24 for a 24GB card)"),
    num_gpus: z.number().int().min(1).optional()
      .describe("Filter by exact number of GPUs per instance"),
  },
  async ({ limit, only_available, max_price_usd, min_vram_gb, num_gpus }) => {
    try {
      const raw = await client.listInstanceTypes({
        available: only_available ? true : undefined,
        sort: "price",
        minVram: min_vram_gb,
        maxPriceUsd: max_price_usd,
        numGpus: num_gpus,
      });

      let offers = client.normalizeOffers(raw);

      // Sort by total hourly price (Shadeform already returns sorted, but ensure it)
      offers.sort((a, b) => a.price_per_hour_usd - b.price_per_hour_usd);
      offers = offers.slice(0, limit);

      return {
        content: [{ type: "text", text: formatOfferTable(offers) }],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error fetching GPU prices: ${err}` }],
        isError: true,
      };
    }
  }
);

// ─── Tool: filter_by_gpu_type ─────────────────────────────────────────────────

server.tool(
  "filter_by_gpu_type",
  "Search for GPU instances by GPU model name (e.g. 'A100', 'H100', 'RTX4090', 'L40S'). " +
  "Returns all matching offers sorted by price. Read-only — no money is spent.",
  {
    gpu_type: z.string().min(1)
      .describe("GPU model name, e.g. 'A100', 'H100', 'A6000', 'RTX4090', 'L40S', 'A10'"),
    only_available: z.boolean().default(true)
      .describe("Only show instances currently available (default: true)"),
    max_price_usd: z.number().positive().optional()
      .describe("Maximum total price per hour in USD"),
    num_gpus: z.number().int().min(1).optional()
      .describe("Filter by number of GPUs per instance"),
  },
  async ({ gpu_type, only_available, max_price_usd, num_gpus }) => {
    try {
      const raw = await client.listInstanceTypes({
        gpuType: gpu_type,
        available: only_available ? true : undefined,
        sort: "price",
        maxPriceUsd: max_price_usd,
        numGpus: num_gpus,
      });

      const offers = client.normalizeOffers(raw)
        .sort((a, b) => a.price_per_hour_usd - b.price_per_hour_usd);

      if (offers.length === 0) {
        return {
          content: [{
            type: "text",
            text: `No offers found for GPU type "${gpu_type}".\n` +
              "Try a broader search term (e.g. 'A100' instead of 'A100_80G') " +
              "or set only_available=false to see all entries including unavailable ones.",
          }],
        };
      }

      return {
        content: [{ type: "text", text: formatOfferTable(offers) }],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error searching for GPU type: ${err}` }],
        isError: true,
      };
    }
  }
);

// ─── Tool: rent_instance ──────────────────────────────────────────────────────

server.tool(
  "rent_instance",
  "⚠️ SPENDS MONEY — Launch a GPU instance via Shadeform. " +
  "Use list_cheapest_gpus or filter_by_gpu_type first to find the cloud, region, and shade_instance_type. " +
  "The instance starts billing immediately upon creation.",
  {
    cloud: z.string().min(1)
      .describe("Cloud provider name exactly as shown by list_cheapest_gpus (e.g. 'lambda', 'hyperstack', 'tensordock')"),
    region: z.string().min(1)
      .describe("Region exactly as shown by list_cheapest_gpus (e.g. 'us-east-1', 'canada-1')"),
    shade_instance_type: z.string().min(1)
      .describe("Shadeform instance type exactly as shown (e.g. 'A100_80G', 'H100_SXM', 'A6000')"),
    name: z.string().min(1).default("gpu-instance")
      .describe("Name for the instance (default: 'gpu-instance')"),
    shade_cloud: z.boolean().default(true)
      .describe("Use Shade Cloud (no separate cloud account needed). Default: true"),
    docker_image: z.string().optional()
      .describe("Optional: Docker image to pull and run on startup (e.g. 'vllm/vllm-openai:latest')"),
    docker_args: z.string().optional()
      .describe("Optional: Arguments to pass to the Docker container"),
    startup_script_base64: z.string().optional()
      .describe("Optional: Base64-encoded bash startup script (alternative to docker_image)"),
    confirm: z.boolean()
      .describe("Must be set to TRUE to actually create the instance. Safety gate — prevents accidental launches."),
  },
  async ({
    cloud, region, shade_instance_type, name, shade_cloud,
    docker_image, docker_args, startup_script_base64, confirm
  }) => {
    if (!confirm) {
      return {
        content: [{
          type: "text",
          text: [
            "⚠️  CONFIRMATION REQUIRED",
            "",
            "You are about to launch a GPU instance that will be billed immediately.",
            "To proceed, call rent_instance again with confirm=true.",
            "",
            `Details:`,
            `  Cloud:  ${cloud}`,
            `  Region: ${region}`,
            `  Type:   ${shade_instance_type}`,
            `  Name:   ${name}`,
            docker_image ? `  Image:  ${docker_image}` : "",
            "",
            "Set confirm=true to launch.",
          ].filter(s => s !== undefined).join("\n"),
        }],
      };
    }

    try {
      const req: Parameters<typeof client.createInstance>[0] = {
        cloud,
        region,
        shade_instance_type,
        shade_cloud,
        name,
      };

      if (docker_image) {
        req.launch_configuration = {
          type: "docker",
          docker_configuration: {
            image: docker_image,
            ...(docker_args ? { args: docker_args } : {}),
          },
        };
      } else if (startup_script_base64) {
        req.launch_configuration = {
          type: "script",
          script_configuration: { base64_script: startup_script_base64 },
        };
      }

      const result = await client.createInstance(req);

      return {
        content: [{
          type: "text",
          text: [
            "✅ Instance launched successfully!",
            "",
            `Instance ID:       ${result.id}`,
            `Cloud Instance ID: ${result.cloud_assigned_id}`,
            "",
            "The instance is now provisioning. It may take a few minutes to become active.",
            `Use get_instance_info with id="${result.id}" to check status and get SSH access details.`,
            `Use stop_instance with id="${result.id}" to terminate and stop billing.`,
          ].join("\n"),
        }],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error creating instance: ${err}` }],
        isError: true,
      };
    }
  }
);

// ─── Tool: list_my_instances ──────────────────────────────────────────────────

server.tool(
  "list_my_instances",
  "List all your current GPU instances across all cloud providers. Read-only.",
  {},
  async () => {
    try {
      const instances = await client.listInstances();

      if (instances.length === 0) {
        return {
          content: [{
            type: "text",
            text: "No active instances found. Use rent_instance to launch one.",
          }],
        };
      }

      const lines = [
        `You have ${instances.length} instance(s):\n`,
        ...instances.map((inst, i) => {
          const hourly = inst.hourly_price
            ? `$${(inst.hourly_price / 100).toFixed(3)}/hr`
            : "N/A";
          return [
            `${i + 1}. [${inst.status.toUpperCase()}] ${inst.name}`,
            `   ID: ${inst.id}`,
            `   ${inst.cloud} / ${inst.region} — ${inst.shade_instance_type}`,
            `   GPU: ${inst.configuration.gpu_type} × ${inst.configuration.num_gpus}`,
            `   Price: ${hourly} | Total: $${inst.cost_estimate}`,
            `   IP: ${inst.ip || "pending..."}`,
            "",
          ].join("\n");
        }),
        "Use get_instance_info for full details, stop_instance to terminate.",
      ];

      return {
        content: [{ type: "text", text: lines.join("") }],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error listing instances: ${err}` }],
        isError: true,
      };
    }
  }
);

// ─── Tool: get_instance_info ──────────────────────────────────────────────────

server.tool(
  "get_instance_info",
  "Get full details for a specific GPU instance including IP address, SSH access, status, and cost. Read-only.",
  {
    id: z.string().uuid()
      .describe("Instance ID (UUID) — get this from list_my_instances or rent_instance response"),
  },
  async ({ id }) => {
    try {
      const inst = await client.getInstance(id);
      return {
        content: [{ type: "text", text: formatInstance(inst as Parameters<typeof formatInstance>[0]) }],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error fetching instance ${id}: ${err}` }],
        isError: true,
      };
    }
  }
);

// ─── Tool: stop_instance ──────────────────────────────────────────────────────

server.tool(
  "stop_instance",
  "⚠️ DESTRUCTIVE — Permanently delete and terminate a GPU instance. " +
  "This immediately stops billing but also destroys all data on the instance. " +
  "This action cannot be undone.",
  {
    id: z.string().uuid()
      .describe("Instance ID (UUID) to terminate — get this from list_my_instances"),
    confirm: z.boolean()
      .describe("Must be set to TRUE to actually delete the instance. Safety gate."),
  },
  async ({ id, confirm }) => {
    if (!confirm) {
      return {
        content: [{
          type: "text",
          text: [
            "⚠️  CONFIRMATION REQUIRED",
            "",
            `You are about to permanently DELETE instance ${id}.`,
            "This will immediately stop billing but destroy all data on the instance.",
            "This CANNOT be undone.",
            "",
            "Call stop_instance again with confirm=true to proceed.",
          ].join("\n"),
        }],
      };
    }

    try {
      await client.deleteInstance(id);
      return {
        content: [{
          type: "text",
          text: `✅ Instance ${id} has been deleted successfully. Billing has stopped.`,
        }],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error deleting instance ${id}: ${err}` }],
        isError: true,
      };
    }
  }
);

// ─── Start ────────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write("gpu-rental-mcp started — ready for requests\n");
