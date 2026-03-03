# Governance Model (Platform-Neutral)

This document provides an end-to-end explanation of the governance system using platform-neutral diagrams.

Key references:
- Constitution: `../constitution/AI_ENGINEERING_CONSTITUTION.md`
- Bootstrap protocol: `../bootstrap/BOOTSTRAP_PROMPT.md`
- Project interrogation: `../bootstrap/project-interrogation.md`
- Guardrails: `../guardrails/baseline-rules.yaml`
- Validation patterns: `../guardrails/validation-patterns.yaml`
- Learning loop: `../learning/lessons-schema.md`
- Agent contract: `../agents/agent-behaviour.md`

## 1) Governance Architecture
```mermaid
flowchart TB
	subgraph Repo[Governed Repository]
		GOV[Governance Artifacts\n(.governance/*)]
		PROF[Project Profile\nproject-profile.json]
		MAN[System Manifest\nsystem-manifest.json]
		GR[Guardrails\nbaseline-rules.yaml]
		VP[Validation Patterns\nvalidation-patterns.yaml]
		EVD[Evidence Store\n(.governance/evidence/*)]
		LL[Learning Records\n(.governance/learning/*)]
	end

	AG[AI Agent]
	H[Human Approver]

	AG -->|reads| GOV
	GOV --> PROF
	GOV --> MAN
	GOV --> GR
	GOV --> VP

	AG -->|produces evidence| EVD
	AG -->|records incidents/proposals| LL
	LL -->|approval required| H
	H -->|approves updates| GOV
```

## 2) Bootstrap Flow
```mermaid
flowchart LR
	P0[Phase 0\nInvocation Rules] --> P1[Phase 1\nProject Interrogation]
	P1 --> P2[Phase 2\nEnvironment Discovery]
	P2 --> P3[Phase 3\nSystem Manifest Creation]
	P3 --> P4[Phase 4\nGuardrail Installation]
	P4 --> P5[Phase 5\nTask Governance Activation]
	P5 --> P6[Phase 6\nLearning System Initialization]
	P6 --> P7[Phase 7\nGovernance Status Report]
```

## 3) Agent Execution Loop
```mermaid
flowchart TD
	I[Interrogate\nread repo + governance] --> V[Validate\ndoctor checks]
	V --> P[Plan\nintent + evidence plan]
	P --> E[Execute\nminimal visible changes]
	E --> X[Verify\nrun validations]
	X --> L[Learn\nrecord incident/proposal]
	L --> I
```

## 4) Learning Feedback Loop
```mermaid
flowchart TB
	INC[Incident] --> ANA[Analysis]
	ANA --> PROP[Guardrail Proposal]
	PROP --> APPR{Human Approval?}
	APPR -- Approved --> UPD[Governance Update]
	APPR -- Rejected --> NOTE[Record decision + rationale]
	UPD --> PREV[Prevent recurrence\nnew rules/patterns]
	PREV --> INC
```
