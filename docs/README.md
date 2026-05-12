# Unified Trading System Documentation

Welcome to the comprehensive documentation for the Unified Trading System. This system combines LVR's microstructure analysis with Autonomous Systems' POMDP formulation to create an adaptive, learning trading agent.

## Documentation Structure

- **[Getting Started](./getting-started/index.md)**: Role-specific guides to get you up and running in under 30 minutes
- **[Architecture](./architecture/overview.md)**: Deep dive into the system's six-layer architecture
- **[Reference](./reference/configuration.md)**: Complete API, configuration, and troubleshooting references
- **[Tutorials](./tutorials/)**: Hands-on guides for extending and customizing the system
- **[Research](./research/)**: Technical deep dives into the quantitative foundations

## Quick Access by Role

| Role | Start Here |
|------|------------|
| Quantitative Developer | [Getting Started for Quant Devs](./getting-started/quantitative-developer.md) |
| Software Architect | [Getting Started for Architects](./getting-started/software-architect.md) |
| AI/ML Engineer | [Getting Started for AI/ML](./getting-started/ai-ml-engineer.md) |
| Data Engineer | [Getting Started for Data Eng](./getting-started/data-engineer.md) |
| SRE/DevOps | [Getting Started for SRE](./getting-started/sre.md) |
| Capital Allocator/HF Manager | [Getting Started for Investors](./getting-started/capital-allocator.md) |
| UX Designer | [Getting Started for UX](./getting-started/ux-designer.md) |

## System Overview

The Unified Trading System implements:

- **Unified Belief State**: Combines LVR microstructure features (OFI, I*, L*, S*) with POMDP regime detection
- **Adaptive Learning**: Lyapunov-stable aggression controller that learns from execution feedback
- **Advanced Risk Management**: Nonlinear risk manifold with five-level protection system
- **Smart Order Execution**: Market-aware order routing with minimal slippage and latency
- **Full Observability**: Structured logging, Prometheus metrics, health checks, and multi-channel alerting
- **Online Adaptation**: Concept drift detection and automatic parameter tuning

## Getting Started

Choose your role-specific guide above to begin, or start with the [general quick start](./getting-started/index.md).

---

*Documentation auto-generated from source code. Last updated: $(date)*