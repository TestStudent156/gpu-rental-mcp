/**
 * Shadeform API Client
 * Covers 30+ cloud providers via a single API key.
 * Base URL: https://api.shadeform.ai/v1
 * Auth: x-api-key header
 */

const BASE_URL = "https://api.shadeform.ai/v1";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface InstanceType {
  cloud: string;
  region: string;
  shade_instance_type: string;
  cloud_instance_type: string;
  configuration: {
    memory_in_gb: number;
    storage_in_gb: number;
    vcpus: number;
    num_gpus: number;
    gpu_type: string;
    interconnect: string;
    vram_per_gpu_in_gb: number;
    gpu_manufacturer: string;
    nvlink?: boolean;
  };
  hourly_price: number; // in cents
  availability: boolean;
  boot_time?: {
    min_boot_in_sec: number;
    max_boot_in_sec: number;
  };
}

export interface Instance {
  id: string;
  cloud: string;
  region: string;
  shade_instance_type: string;
  cloud_instance_type: string;
  cloud_assigned_id: string;
  shade_cloud: boolean;
  name: string;
  configuration: {
    memory_in_gb: number;
    storage_in_gb: number;
    vcpus: number;
    num_gpus: number;
    gpu_type: string;
    interconnect: string;
    vram_per_gpu_in_gb: number;
    gpu_manufacturer: string;
    os: string;
  };
  ip: string;
  ssh_user: string;
  ssh_port: number;
  status: "creating" | "pending_provider" | "pending" | "active" | "error" | "deleting" | "deleted";
  status_details?: string;
  cost_estimate: string;
  hourly_price?: number;
  created_at: string;
  deleted_at: string;
  active_at?: string;
}

export interface CreateInstanceRequest {
  cloud: string;
  region: string;
  shade_instance_type: string;
  shade_cloud?: boolean;
  name: string;
  launch_configuration?: {
    type: "docker" | "script";
    docker_configuration?: {
      image: string;
      args?: string;
      envs?: Array<{ name: string; value: string }>;
      port_mappings?: Array<{ host_port: number; container_port: number }>;
    };
    script_configuration?: {
      base64_script: string;
    };
  };
}

export interface CreateInstanceResponse {
  id: string;
  cloud_assigned_id: string;
}

// ─── Normalized offer for cross-provider comparison ───────────────────────────

export interface NormalizedOffer {
  provider: string;         // e.g. "lambda" via Shadeform
  cloud: string;            // Shadeform cloud name
  region: string;
  shade_instance_type: string;
  cloud_instance_type: string;
  gpu_type: string;
  num_gpus: number;
  vram_per_gpu_gb: number;
  total_vram_gb: number;
  vcpus: number;
  ram_gb: number;
  storage_gb: number;
  price_per_hour_usd: number;       // normalized from cents
  price_per_gpu_hour_usd: number;   // per single GPU
  available: boolean;
  interconnect: string;
}

// ─── API Client ───────────────────────────────────────────────────────────────

export class ShadeformClient {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  private get headers(): Record<string, string> {
    return {
      "x-api-key": this.apiKey,
      "Content-Type": "application/json",
    };
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${BASE_URL}${path}`;
    const res = await fetch(url, {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Shadeform API ${method} ${path} → ${res.status}: ${text}`);
    }

    return res.json() as Promise<T>;
  }

  /** List all available instance types with live pricing */
  async listInstanceTypes(opts: {
    gpuType?: string;
    numGpus?: number;
    available?: boolean;
    sort?: "price";
    minVram?: number;
    maxPriceUsd?: number;
  } = {}): Promise<InstanceType[]> {
    const params = new URLSearchParams();
    if (opts.gpuType) params.set("gpu_type", opts.gpuType);
    if (opts.numGpus) params.set("num_gpus", String(opts.numGpus));
    if (opts.available !== undefined) params.set("available", String(opts.available));
    if (opts.sort) params.set("sort", opts.sort);

    const query = params.toString() ? `?${params}` : "";
    const data = await this.request<{ instance_types: InstanceType[] }>(
      "GET",
      `/instances/types${query}`
    );

    let types = data.instance_types ?? [];

    // Client-side filters
    if (opts.minVram !== undefined) {
      types = types.filter(t => t.configuration.vram_per_gpu_in_gb >= opts.minVram!);
    }
    if (opts.maxPriceUsd !== undefined) {
      types = types.filter(t => t.hourly_price / 100 <= opts.maxPriceUsd!);
    }

    return types;
  }

  /** Normalize raw Shadeform instance types into a uniform comparison format */
  normalizeOffers(types: InstanceType[]): NormalizedOffer[] {
    return types.map(t => {
      const priceUsd = t.hourly_price / 100;
      const numGpus = t.configuration.num_gpus || 1;
      return {
        provider: t.cloud,
        cloud: t.cloud,
        region: t.region,
        shade_instance_type: t.shade_instance_type,
        cloud_instance_type: t.cloud_instance_type,
        gpu_type: t.configuration.gpu_type,
        num_gpus: numGpus,
        vram_per_gpu_gb: t.configuration.vram_per_gpu_in_gb,
        total_vram_gb: t.configuration.vram_per_gpu_in_gb * numGpus,
        vcpus: t.configuration.vcpus,
        ram_gb: t.configuration.memory_in_gb,
        storage_gb: t.configuration.storage_in_gb,
        price_per_hour_usd: priceUsd,
        price_per_gpu_hour_usd: parseFloat((priceUsd / numGpus).toFixed(4)),
        available: t.availability,
        interconnect: t.configuration.interconnect,
      };
    });
  }

  /** Get all active instances */
  async listInstances(): Promise<Instance[]> {
    const data = await this.request<{ instances: Instance[] }>("GET", "/instances");
    return data.instances ?? [];
  }

  /** Get details for a single instance */
  async getInstance(id: string): Promise<Instance> {
    const data = await this.request<{ instance: Instance }>("GET", `/instances/${id}/info`);
    return data.instance;
  }

  /** Create (rent) a new instance */
  async createInstance(req: CreateInstanceRequest): Promise<CreateInstanceResponse> {
    return this.request<CreateInstanceResponse>("POST", "/instances/create", req);
  }

  /** Delete (stop/terminate) an instance */
  async deleteInstance(id: string): Promise<void> {
    await this.request<unknown>("POST", `/instances/${id}/delete`);
  }

  /** Restart an instance */
  async restartInstance(id: string): Promise<void> {
    await this.request<unknown>("POST", `/instances/${id}/restart`);
  }
}
