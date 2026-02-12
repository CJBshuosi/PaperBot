import {
    Paper,
    PaperDetails,
    Scholar,
    ScholarDetails,
    Stats,
    WikiConcept,
    TrendingTopic,
    TimelineItem,
    SavedPaper,
    LLMUsageSummary,
    DeadlineRadarItem,
} from "./types"

const API_BASE_URL = (process.env.PAPERBOT_API_BASE_URL || "http://127.0.0.1:8000") + "/api"

function slugToName(slug: string): string {
    return slug
        .split("-")
        .filter(Boolean)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ")
}

async function postJson<T>(path: string, payload: Record<string, unknown>): Promise<T | null> {
    try {
        const res = await fetch(`${API_BASE_URL}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            cache: "no-store",
        })
        if (!res.ok) return null
        return await res.json() as T
    } catch {
        return null
    }
}

export async function fetchStats(): Promise<Stats> {
    try {
        const usage = await fetchLLMUsage()
        const tokenCount = usage.totals.total_tokens
        const prettyTokens = tokenCount >= 1000 ? `${Math.round(tokenCount / 1000)}k` : `${tokenCount}`
        return {
            tracked_scholars: 128,
            new_papers: 12,
            llm_usage: prettyTokens,
            read_later: 8,
        }
    } catch {
        // Keep resilient dashboard fallback.
    }

    return {
        tracked_scholars: 128,
        new_papers: 12,
        llm_usage: "45k",
        read_later: 8
    }
}

export async function fetchActivities(): Promise<TimelineItem[]> {
    try {
        const papers = await fetchPapers()
        const items: TimelineItem[] = papers.slice(0, 10).map((p, i) => ({
            id: `tl-${i}`,
            kind: p.status === "Saved" ? "save" as const : "harvest" as const,
            title: p.title,
            subtitle: p.venue,
            timestamp: "recently",
        }))
        return items
    } catch {
        return []
    }
}

export async function fetchTrendingTopics(): Promise<TrendingTopic[]> {
    return [
        { text: "Large Language Models", value: 100 },
        { text: "Transformer", value: 80 },
        { text: "Reinforcement Learning", value: 60 },
        { text: "Generative AI", value: 90 },
        { text: "Computer Vision", value: 50 },
        { text: "Diffusion Models", value: 70 },
        { text: "Prompt Engineering", value: 40 },
        { text: "Ethics", value: 30 }
    ]
}

export async function fetchSavedPapers(): Promise<SavedPaper[]> {
    try {
        const papers = await fetchPapers()
        return papers
            .filter((p) => p.status === "Saved")
            .slice(0, 5)
            .map((p) => ({
                id: p.id,
                paper_id: p.id,
                title: p.title,
                authors: p.authors,
                saved_at: "recently",
            }))
    } catch {
        return []
    }
}

export async function fetchLLMUsage(days: number = 7): Promise<LLMUsageSummary> {
    try {
        const qs = new URLSearchParams({ days: String(days) })
        // Use Next.js proxy route for SSR compatibility
        const url = typeof window === "undefined"
            ? `${API_BASE_URL}/model-endpoints/usage?${qs.toString()}`
            : `/api/model-endpoints/usage?${qs.toString()}`
        const res = await fetch(url, { cache: "no-store" })
        if (!res.ok) throw new Error("usage endpoint unavailable")
        const payload = await res.json() as { summary?: LLMUsageSummary }
        if (payload.summary) {
            return payload.summary
        }
    } catch {
        // Keep static fallback for local-first UX.
    }

    return {
        window_days: days,
        daily: [
            {
                date: "Mon",
                total_tokens: 23000,
                total_cost_usd: 0.0,
                providers: { openai: 12000, anthropic: 8000, ollama: 3000 },
            },
            {
                date: "Tue",
                total_tokens: 28500,
                total_cost_usd: 0.0,
                providers: { openai: 15000, anthropic: 9500, ollama: 4000 },
            },
            {
                date: "Wed",
                total_tokens: 22000,
                total_cost_usd: 0.0,
                providers: { openai: 10000, anthropic: 7000, ollama: 5000 },
            },
            {
                date: "Thu",
                total_tokens: 32000,
                total_cost_usd: 0.0,
                providers: { openai: 18000, anthropic: 12000, ollama: 2000 },
            },
        ],
        provider_models: [],
        totals: {
            calls: 0,
            total_tokens: 105500,
            total_cost_usd: 0,
        },
    }
}

export async function fetchDeadlineRadar(userId: string = "default"): Promise<DeadlineRadarItem[]> {
    try {
        const qs = new URLSearchParams({
            user_id: userId,
            days: "180",
            ccf_levels: "A,B,C",
            limit: "10",
        })
        const res = await fetch(`${API_BASE_URL}/research/deadlines/radar?${qs.toString()}`, {
            cache: "no-store",
        })
        if (!res.ok) return []
        const payload = await res.json() as { items?: DeadlineRadarItem[] }
        return payload.items || []
    } catch {
        return []
    }
}


export async function fetchScholars(): Promise<Scholar[]> {
    // Mock data for now
    return [
        {
            id: "dawn-song",
            name: "Dawn Song",
            affiliation: "UC Berkeley",
            h_index: 120,
            papers_tracked: 45,
            recent_activity: "Published 2 days ago",
            status: "active"
        },
        {
            id: "kaiming-he",
            name: "Kaiming He",
            affiliation: "MIT",
            h_index: 145,
            papers_tracked: 28,
            recent_activity: "Cited 500+ times this week",
            status: "active"
        },
        {
            id: "yann-lecun",
            name: "Yann LeCun",
            affiliation: "Meta AI / NYU",
            h_index: 180,
            papers_tracked: 15,
            recent_activity: "New interview",
            status: "idle"
        }
    ]
}

export async function fetchPaperDetails(id: string): Promise<PaperDetails> {
    // Mock data
    return {
        id,
        title: "Attention Is All You Need",
        venue: "NeurIPS 2017",
        authors: "Vaswani et al.",
        citations: "100k+",
        status: "Reproduced",
        tags: ["Transformer", "NLP"],
        abstract: "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        tldr: "PROPOSED the Transformer, a novel network architecture based solely on attention mechanisms, which achieves state-of-the-art results in machine translation tasks while being parallelizable and requiring significantly less training time.",
        pis_score: 98,
        impact_radar: [
            { subject: 'Novelty', A: 120, fullMark: 150 },
            { subject: 'Accessibility', A: 98, fullMark: 150 },
            { subject: 'Rigor', A: 86, fullMark: 150 },
            { subject: 'Reproducibility', A: 99, fullMark: 150 },
            { subject: 'Impact', A: 145, fullMark: 150 },
            { subject: 'Clarity', A: 110, fullMark: 150 },
        ],
        sentiment_analysis: [
            { name: 'Positive', value: 400, fill: '#4ade80' },
            { name: 'Neutral', value: 300, fill: '#94a3b8' },
            { name: 'Critical', value: 50, fill: '#f87171' },
        ],
        citation_velocity: [
            { month: 'Jan', citations: 400 },
            { month: 'Feb', citations: 800 },
            { month: 'Mar', citations: 1200 },
            { month: 'Apr', citations: 2000 },
            { month: 'May', citations: 3500 },
            { month: 'Jun', citations: 5000 },
        ],
        reproduction: {
            status: "Success",
            logs: [
                "[INFO] Environment inferred: PyTorch 2.1, CUDA 12.1",
                "[INFO] Installing dependencies...",
                "[SUCCESS] Dependencies installed",
                "[INFO] Starting training loop...",
                "[INFO] Epoch 1: Loss 2.45",
                "[SUCCESS] Reproduction verification passed (BLEU > 28.0)"
            ],
            dockerfile: "FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime\nRUN pip install transformers datasets\nCOPY . /app\nWORKDIR /app\nCMD [\"python\", \"train.py\"]"
        }
    }
}

// TODO: add unit tests for fetchScholarDetails — cover successful network+trends,
//  partial responses, and both-null fallback path.
export async function fetchScholarDetails(id: string): Promise<ScholarDetails> {
    const scholarName = slugToName(id)

    type ScholarNetworkResponse = {
        scholar?: { name?: string; affiliations?: string[]; citation_count?: number; paper_count?: number; h_index?: number }
        stats?: { papers_used?: number }
        nodes?: Array<{ name?: string; type?: string; collab_papers?: number }>
    }

    type ScholarTrendsResponse = {
        scholar?: { name?: string; affiliations?: string[]; citation_count?: number; paper_count?: number; h_index?: number }
        trend_summary?: { publication_trend?: "up" | "down" | "flat"; citation_trend?: "up" | "down" | "flat" }
        topic_distribution?: Array<{ topic?: string; count?: number }>
        recent_papers?: Array<{ title?: string; year?: number; citation_count?: number; venue?: string; url?: string }>
    }

    const [network, trends] = await Promise.all([
        postJson<ScholarNetworkResponse>("/research/scholar/network", {
            scholar_name: scholarName,
            max_papers: 120,
            recent_years: 5,
            max_nodes: 30,
        }),
        postJson<ScholarTrendsResponse>("/research/scholar/trends", {
            scholar_name: scholarName,
            max_papers: 200,
            year_window: 10,
        }),
    ])

    // TODO: mock fallback is hardcoded to Dawn Song — replace with generic
    //  placeholder or remove entirely once real scholar data is always available.
    // Fallback to mock data if the scholar is not configured in subscriptions yet.
    if (!network && !trends) {
        const papers = await fetchPapers()
        return {
            id,
            name: scholarName,
            affiliation: "University of California, Berkeley",
            h_index: 120,
            papers_tracked: 45,
            recent_activity: "Published 2 days ago",
            status: "active",
            bio: "Dawn Song is a Professor in the Department of Electrical Engineering and Computer Science at UC Berkeley. Her research interest lies in deep learning, security, and blockchain.",
            location: "Berkeley, CA",
            website: "https://dawnsong.io",
            expertise_radar: [
                { subject: "Security", A: 100, fullMark: 100 },
                { subject: "Deep Learning", A: 90, fullMark: 100 },
                { subject: "Blockchain", A: 80, fullMark: 100 },
                { subject: "Systems", A: 85, fullMark: 100 },
                { subject: "Privacy", A: 95, fullMark: 100 },
            ],
            publications: papers,
            co_authors: [
                { name: "Dan Hendrycks", avatar: "https://avatar.vercel.sh/dan.png" },
                { name: "Kevin Eykholt", avatar: "https://avatar.vercel.sh/kevin.png" },
            ],
            stats: {
                total_citations: 54321,
                papers_count: 230,
                h_index: 120,
            },
        }
    }

    const scholar = network?.scholar || trends?.scholar || {}
    const topicDist = (trends?.topic_distribution || []).slice(0, 5)
    const maxTopicCount = Math.max(1, ...topicDist.map((t) => Number(t.count || 0)))

    const publications: Paper[] = (trends?.recent_papers || []).slice(0, 15).map((paper, idx) => ({
        id: `sch-${id}-paper-${idx}`,
        title: String(paper.title || "Untitled"),
        venue: String(paper.venue || "Unknown venue"),
        authors: String(scholar.name || scholarName),
        citations: Number(paper.citation_count || 0),
        status: "analyzing",
        tags: topicDist.map((t) => String(t.topic || "")).filter(Boolean).slice(0, 3),
    }))

    const coauthors = (network?.nodes || [])
        .filter((n) => n.type === "coauthor")
        .slice(0, 12)
        .map((n) => {
            const name = String(n.name || "Unknown")
            const collab = Number(n.collab_papers || 0)
            return {
                name: collab > 0 ? `${name} (${collab})` : name,
                avatar: `https://avatar.vercel.sh/${encodeURIComponent(name)}.png`,
            }
        })

    const publicationTrend = trends?.trend_summary?.publication_trend || "flat"
    const recentActivity = publicationTrend === "up"
        ? "Publication trend up"
        : publicationTrend === "down"
            ? "Publication trend down"
            : "Publication trend stable"

    return {
        id,
        name: String(scholar.name || scholarName),
        affiliation: String((scholar.affiliations || ["Unknown affiliation"])[0] || "Unknown affiliation"),
        h_index: Number(scholar.h_index || 0),
        papers_tracked: Number(scholar.paper_count || 0),
        recent_activity: recentActivity,
        status: publicationTrend === "up" ? "active" : "idle",
        bio: `Trend snapshot: ${trends?.trend_summary?.citation_trend || "flat"} citation trend over the recent analysis window.`,
        location: "N/A",
        website: "",
        expertise_radar: topicDist.map((t) => ({
            subject: String(t.topic || "Topic"),
            A: Math.round((Number(t.count || 0) / maxTopicCount) * 100),
            fullMark: 100,
        })),
        publications,
        co_authors: coauthors,
        stats: {
            total_citations: Number(scholar.citation_count || 0),
            papers_count: Number(scholar.paper_count || 0),
            h_index: Number(scholar.h_index || 0),
        },
    }
}

export async function fetchWikiConcepts(): Promise<WikiConcept[]> {
    return [
        {
            id: "transformer",
            name: "Transformer",
            description: "A deep learning model architecture relying on self-attention mechanisms.",
            definition: "The Transformer architecture processes input sequences in parallel using self-attention, allowing it to capture long-range dependencies more effectively than RNNs. It consists of encoder and decoder stacks, each containing multi-head attention and feed-forward layers.",
            related_papers: ["Attention Is All You Need", "BERT", "GPT-3"],
            related_concepts: ["Self-Attention", "Positional Encoding", "Multi-Head Attention"],
            examples: ["GPT-4", "Claude", "LLaMA"],
            category: "Architecture",
            icon: "layers"
        },
        {
            id: "rlhf",
            name: "RLHF",
            description: "Reinforcement Learning from Human Feedback, used to align LLMs with human preferences.",
            definition: "RLHF trains a reward model on human preference data, then fine-tunes the language model using PPO to maximize the reward. This alignment technique helps reduce harmful outputs and improve helpfulness.",
            related_papers: ["InstructGPT", "Constitutional AI"],
            related_concepts: ["PPO", "Reward Model", "Alignment"],
            examples: ["ChatGPT alignment", "Claude training"],
            category: "Method",
            icon: "target"
        },
        {
            id: "bleu",
            name: "BLEU Score",
            description: "A metric for evaluating the quality of machine translated text.",
            definition: "BLEU (Bilingual Evaluation Understudy) compares n-gram overlaps between generated and reference translations. Scores range from 0 to 1, with higher scores indicating better translation quality.",
            related_papers: ["BLEU: a Method for Automatic Evaluation"],
            related_concepts: ["ROUGE", "METEOR", "BERTScore"],
            examples: ["MT evaluation", "Summarization scoring"],
            category: "Metric",
            icon: "bar-chart"
        },
        {
            id: "diffusion",
            name: "Diffusion Models",
            description: "Generative models that learn to reverse a gradual noising process.",
            definition: "Diffusion models add Gaussian noise to data over multiple steps, then learn to reverse this process. They achieve state-of-the-art image generation by iteratively denoising random noise into coherent samples.",
            related_papers: ["DDPM", "Stable Diffusion", "DALL-E 2"],
            related_concepts: ["Denoising", "Score Matching", "Latent Diffusion"],
            examples: ["Midjourney", "Stable Diffusion XL"],
            category: "Method",
            icon: "waves"
        },
        {
            id: "imagenet",
            name: "ImageNet",
            description: "Large-scale visual database for object recognition research.",
            definition: "ImageNet contains over 14 million images annotated with 20,000+ categories. The ILSVRC subset (1000 classes) became the standard benchmark for image classification, driving major advances in CNNs.",
            related_papers: ["ImageNet Classification with Deep CNNs"],
            related_concepts: ["Transfer Learning", "Fine-tuning", "Pretraining"],
            examples: ["ResNet-50 on ImageNet", "ViT benchmarks"],
            category: "Dataset",
            icon: "image"
        }
    ]
}

export async function fetchPapers(): Promise<Paper[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/papers/library`)
        if (!res.ok) {
            console.error("Failed to fetch papers library:", res.status)
            return []
        }
        const data = await res.json()
        // Transform backend response to frontend Paper type
        return (data.papers || []).map((item: { paper: Record<string, unknown>; action: string }) => ({
            id: String(item.paper.id),
            title: item.paper.title || "Untitled",
            venue: item.paper.venue || "Unknown",
            authors: Array.isArray(item.paper.authors) ? item.paper.authors.join(", ") : "Unknown",
            citations: item.paper.citation_count ? `${item.paper.citation_count}` : "0",
            status: item.action === "save" ? "Saved" : "pending",
            tags: Array.isArray(item.paper.fields_of_study) ? item.paper.fields_of_study.slice(0, 3) : []
        }))
    } catch (e) {
        console.error("Error fetching papers:", e)
        return []
    }
}
