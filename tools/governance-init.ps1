[CmdletBinding()]
param(
	[Parameter(Position = 0)]
	[string]$TargetPath = ".",

	[switch]$DryRun,
	[switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) {
	Write-Host $Message
}

function Fail([string]$Message) {
	throw $Message
}

function Resolve-FullPath([string]$Path) {
	return (Resolve-Path -LiteralPath $Path).Path
}

function Get-RepoRootFromTools([string]$ToolsDir) {
	return (Resolve-Path -LiteralPath (Join-Path $ToolsDir ".." )).Path
}

function New-IsoTimestampUtc() {
	return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

function New-SessionId([string]$TargetFullPath) {
	$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
	$input = "$TargetFullPath|$stamp"
	$bytes = [Text.Encoding]::UTF8.GetBytes($input)
	$sha = [System.Security.Cryptography.SHA256]::Create()
	try {
		$hash = $sha.ComputeHash($bytes)
	} finally {
		if ($null -ne $sha) { $sha.Dispose() }
	}
	$hex = ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
	$short = $hex.Substring(0, 8)
	return "$stamp-$short"
}

function Json-Line([object]$Obj) {
	return ($Obj | ConvertTo-Json -Depth 50 -Compress)
}

$ToolsDir = $PSScriptRoot
$BootstrapRoot = Get-RepoRootFromTools -ToolsDir $ToolsDir
$TargetFull = Resolve-FullPath $TargetPath

$SourceFiles = @{
	"bootstrap_protocol" = Join-Path $BootstrapRoot "bootstrap\BOOTSTRAP_PROMPT.md"
	"bootstrap_identity" = Join-Path $BootstrapRoot "bootstrap\BOOTSTRAP_IDENTITY.md"
	"execution_spec" = Join-Path $BootstrapRoot "runtime\bootstrap-execution-spec.md"
	"bootstrap_contract" = Join-Path $BootstrapRoot "runtime\project-bootstrap-contract.md"
	"session_start" = Join-Path $BootstrapRoot "agents\session-start.md"
	"capability_registry" = Join-Path $BootstrapRoot "agents\capability-registry.md"
	"evidence_spec" = Join-Path $BootstrapRoot "bootstrap\evidence-spec.md"
	"guardrails" = Join-Path $BootstrapRoot "guardrails\baseline-rules.yaml"
	"validation_patterns" = Join-Path $BootstrapRoot "guardrails\validation-patterns.yaml"
	"governance_version" = Join-Path $BootstrapRoot "governance-version.json"
}

foreach ($k in $SourceFiles.Keys) {
	if (-not (Test-Path -LiteralPath $SourceFiles[$k])) {
		Fail "Missing required bootstrap source file: $($SourceFiles[$k])"
	}
}

$GovDir = Join-Path $TargetFull ".governance"
$EvidenceDir = Join-Path $GovDir "evidence"
$EvidenceFile = Join-Path $EvidenceDir "evidence.jsonl"

if ((Test-Path -LiteralPath $GovDir) -and (-not $Force)) {
	Fail "SAFE MODE: Target already contains .governance/. Refusing. Re-run with -Force to overwrite governed artifacts."
}

$SessionId = New-SessionId -TargetFullPath $TargetFull
$Now = New-IsoTimestampUtc

$CreatedPaths = New-Object System.Collections.Generic.List[string]
$BufferedEvidence = New-Object System.Collections.Generic.List[object]
$EvidenceReady = $false

function Add-Evidence {
	param(
		[string]$Phase,
		[string]$Action,
		[object]$Input,
		[object]$Result,
		[string]$Confidence = "high",
		[string]$Source = "repo_scan",
		[string]$Law = $null,
		[string]$RuleId = $null,
		[string]$Notes = $null,
		[string[]]$Artifacts = $null
	)

	$entry = [ordered]@{
		timestamp  = New-IsoTimestampUtc
		phase      = $Phase
		action     = $Action
		input      = $Input
		result     = $Result
		confidence = $Confidence
		source     = $Source
	}
	if ($Law) { $entry["law"] = $Law }
	if ($RuleId) { $entry["rule_id"] = $RuleId }
	if ($Artifacts) { $entry["artifacts"] = $Artifacts }
	if ($Notes) { $entry["notes"] = $Notes }

	if ($DryRun) {
		Write-Info ("[DRY-RUN] evidence: " + (Json-Line $entry))
		return
	}

	if ($EvidenceReady -and (-not $DryRun)) {
		$line = Json-Line $entry
		Add-Content -LiteralPath $EvidenceFile -Value $line
	} else {
		$BufferedEvidence.Add($entry)
	}
}

function Ensure-Dir([string]$Path) {
	if ($DryRun) {
		Write-Info "[DRY-RUN] mkdir -p $Path"
		return
	}
	if (-not (Test-Path -LiteralPath $Path)) {
		New-Item -ItemType Directory -Path $Path | Out-Null
	}
}

function Write-TextFile([string]$Path, [string]$Content) {
	$dir = Split-Path -Parent $Path
	Ensure-Dir $dir
	if ($DryRun) {
		Write-Info "[DRY-RUN] write $Path"
		return
	}
	Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
}

function Copy-File([string]$Source, [string]$Dest) {
	$dir = Split-Path -Parent $Dest
	Ensure-Dir $dir
	if ($DryRun) {
		Write-Info "[DRY-RUN] copy $Source -> $Dest"
		return
	}
	Copy-Item -LiteralPath $Source -Destination $Dest -Force
}

function Rel([string]$FullPath) {
	if ($FullPath.StartsWith($TargetFull, [StringComparison]::OrdinalIgnoreCase)) {
		$rel = $FullPath.Substring($TargetFull.Length)
		return $rel.TrimStart("\", "/")
	}
	return $FullPath
}

function Track-Created([string]$FullPath) {
	$CreatedPaths.Add((Rel $FullPath))
}

# -------------------------
# Phase 0 — Invocation Rules
# -------------------------
Write-Info "Governance Init (PowerShell)"
Write-Info "Target: $TargetFull"
Write-Info "Session: $SessionId"
$modeParts = @()
if ($DryRun) { $modeParts += 'DRY-RUN' } else { $modeParts += 'WRITE' }
if ($Force) { $modeParts += 'FORCE' } else { $modeParts += 'SAFE' }
Write-Info "Mode: $($modeParts -join ', ')"

Add-Evidence -Phase "phase-0" -Action "bootstrap_invocation" -Input @{ target = $TargetFull; dry_run = [bool]$DryRun; force = [bool]$Force } -Result @{ session_id = $SessionId; scope = "governance-artifacts-only" } -Source "execution_layer" -Law "LAW 2"

# -------------------------
# Phase 1 — Project Interrogation
# -------------------------
function Get-FilteredFiles([string]$Root) {
	$excluded = @("\.governance\", "\.git\", "\node_modules\", "\dist\", "\build\", "\out\", "\.venv\", "\venv\")
	Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction SilentlyContinue |
		Where-Object {
			$full = $_.FullName
			foreach ($ex in $excluded) {
				if ($full -like "*$ex*") { return $false }
			}
			return $true
		}
}

$allFiles = @(Get-FilteredFiles -Root $TargetFull)
$readmes = @(Get-ChildItem -LiteralPath $TargetFull -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "README*" } | Sort-Object FullName)
$policyNames = @("SECURITY*", "CONTRIBUTING*", "CODEOWNERS", "LICENSE*", ".editorconfig")
$policy = foreach ($p in $policyNames) {
	Get-ChildItem -LiteralPath $TargetFull -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like $p }
}
$policy = @($policy | Sort-Object FullName -Unique)

# Root signals for stack detection (no assumptions)
$rootSignalNames = @(
	"package.json", "pyproject.toml", "requirements.txt", "Pipfile", "go.mod", "Cargo.toml",
	"pom.xml", "build.gradle", "build.gradle.kts", "global.json"
)
$rootSignals = foreach ($n in $rootSignalNames) {
	$path = Join-Path $TargetFull $n
	if (Test-Path -LiteralPath $path) { Get-Item -LiteralPath $path }
}
$rootSignals = @($rootSignals | Sort-Object FullName)

# Dependency manager detections
$depManagers = New-Object System.Collections.Generic.List[object]
function Add-DepManager([string]$Name, [string[]]$Manifests, [string[]]$Locks) {
	$depManagers.Add(@{ name = $Name; manifest_paths = @($Manifests | Sort-Object); lock_paths = @($Locks | Sort-Object) })
}

$pkgMan = @($allFiles | Where-Object { $_.Name -eq "package.json" } | ForEach-Object { $_.FullName })
if ($pkgMan.Count -gt 0) {
	$locks = @($allFiles | Where-Object { $_.Name -in @("package-lock.json", "yarn.lock", "pnpm-lock.yaml") } | ForEach-Object { $_.FullName })
	Add-DepManager -Name "node" -Manifests $pkgMan -Locks $locks
}

$pyMan = @($allFiles | Where-Object { $_.Name -in @("pyproject.toml", "requirements.txt", "Pipfile") } | ForEach-Object { $_.FullName })
if ($pyMan.Count -gt 0) {
	$locks = @($allFiles | Where-Object { $_.Name -in @("poetry.lock", "Pipfile.lock") } | ForEach-Object { $_.FullName })
	Add-DepManager -Name "python" -Manifests $pyMan -Locks $locks
}

$goMan = @($allFiles | Where-Object { $_.Name -eq "go.mod" } | ForEach-Object { $_.FullName })
if ($goMan.Count -gt 0) {
	$locks = @($allFiles | Where-Object { $_.Name -eq "go.sum" } | ForEach-Object { $_.FullName })
	Add-DepManager -Name "go" -Manifests $goMan -Locks $locks
}

$rsMan = @($allFiles | Where-Object { $_.Name -eq "Cargo.toml" } | ForEach-Object { $_.FullName })
if ($rsMan.Count -gt 0) {
	$locks = @($allFiles | Where-Object { $_.Name -eq "Cargo.lock" } | ForEach-Object { $_.FullName })
	Add-DepManager -Name "cargo" -Manifests $rsMan -Locks $locks
}

$dotnetMan = @($allFiles | Where-Object { $_.Extension -in @(".sln", ".csproj", ".fsproj", ".vbproj") } | ForEach-Object { $_.FullName })
if ($dotnetMan.Count -gt 0) {
	$locks = @($allFiles | Where-Object { $_.Name -eq "packages.lock.json" } | ForEach-Object { $_.FullName })
	Add-DepManager -Name "dotnet" -Manifests $dotnetMan -Locks $locks
}

$mvnMan = @($allFiles | Where-Object { $_.Name -eq "pom.xml" } | ForEach-Object { $_.FullName })
if ($mvnMan.Count -gt 0) { Add-DepManager -Name "maven" -Manifests $mvnMan -Locks @() }
$gradleMan = @($allFiles | Where-Object { $_.Name -in @("build.gradle", "build.gradle.kts") } | ForEach-Object { $_.FullName })
if ($gradleMan.Count -gt 0) { Add-DepManager -Name "gradle" -Manifests $gradleMan -Locks @() }

# CI detection
$ciDefs = New-Object System.Collections.Generic.List[string]
$githubWorkflows = Join-Path $TargetFull ".github\workflows"
if (Test-Path -LiteralPath $githubWorkflows) { $ciDefs.Add((Rel $githubWorkflows)) }
foreach ($ciFile in @("azure-pipelines.yml", ".gitlab-ci.yml", "Jenkinsfile")) {
	$path = Join-Path $TargetFull $ciFile
	if (Test-Path -LiteralPath $path) { $ciDefs.Add((Rel $path)) }
}
$ciPresent = ($ciDefs.Count -gt 0)

# Container detection
$containerDefs = New-Object System.Collections.Generic.List[string]
$dockerfiles = @($allFiles | Where-Object { $_.Name -like "Dockerfile*" } | ForEach-Object { Rel $_.FullName })
foreach ($d in $dockerfiles) { $containerDefs.Add($d) }
foreach ($cFile in @("docker-compose.yml", "docker-compose.yaml")) {
	$path = Join-Path $TargetFull $cFile
	if (Test-Path -LiteralPath $path) { $containerDefs.Add((Rel $path)) }
}
$devcontainer = Join-Path $TargetFull ".devcontainer"
if (Test-Path -LiteralPath $devcontainer) { $containerDefs.Add((Rel $devcontainer)) }
$containersPresent = ($containerDefs.Count -gt 0)

# Runtime clues
$versionPins = @($allFiles | Where-Object { $_.Name -in @(".tool-versions", ".nvmrc", "global.json", ".python-version", ".node-version") } | ForEach-Object { Rel $_.FullName } | Sort-Object)
$envTemplates = @($allFiles | Where-Object { $_.Name -match "^\.env(\.|$)" -and $_.Name -match "(example|template|sample)" } | ForEach-Object { Rel $_.FullName } | Sort-Object)
$automationPaths = New-Object System.Collections.Generic.List[string]
foreach ($autoName in @("Makefile", "justfile")) {
	$path = Join-Path $TargetFull $autoName
	if (Test-Path -LiteralPath $path) { $automationPaths.Add((Rel $path)) }
}

# Language detection (extension + root signals)
$extToLang = @{
	".ps1" = "PowerShell"; ".py" = "Python"; ".js" = "JavaScript"; ".ts" = "TypeScript"; ".java" = "Java";
	".cs" = "C#"; ".go" = "Go"; ".rs" = "Rust"; ".rb" = "Ruby"; ".php" = "PHP"; ".kt" = "Kotlin";
	".swift" = "Swift"; ".cpp" = "C++"; ".c" = "C"; ".h" = "C/C++ Header"
}

$languageEvidence = @{}
foreach ($f in $allFiles) {
	$ext = $f.Extension
	if ($extToLang.ContainsKey($ext)) {
		$lang = $extToLang[$ext]
		if (-not $languageEvidence.ContainsKey($lang)) {
			$languageEvidence[$lang] = New-Object System.Collections.Generic.List[string]
		}
		if ($languageEvidence[$lang].Count -lt 5) {
			$languageEvidence[$lang].Add((Rel $f.FullName))
		}
	}
}

# Root signal boosts confidence
$signalLang = New-Object System.Collections.Generic.List[object]
if ($pkgMan.Count -gt 0) {
	$signalLang.Add(@{ name = "JavaScript/TypeScript"; confidence = "high"; evidence_paths = @($pkgMan | ForEach-Object { Rel $_ } | Sort-Object | Select-Object -First 3) })
}
if ($pyMan.Count -gt 0) {
	$signalLang.Add(@{ name = "Python"; confidence = "high"; evidence_paths = @($pyMan | ForEach-Object { Rel $_ } | Sort-Object | Select-Object -First 3) })
}
if ($goMan.Count -gt 0) {
	$signalLang.Add(@{ name = "Go"; confidence = "high"; evidence_paths = @($goMan | ForEach-Object { Rel $_ } | Sort-Object | Select-Object -First 3) })
}
if ($rsMan.Count -gt 0) {
	$signalLang.Add(@{ name = "Rust"; confidence = "high"; evidence_paths = @($rsMan | ForEach-Object { Rel $_ } | Sort-Object | Select-Object -First 3) })
}
if ($dotnetMan.Count -gt 0) {
	$signalLang.Add(@{ name = ".NET"; confidence = "high"; evidence_paths = @($dotnetMan | ForEach-Object { Rel $_ } | Sort-Object | Select-Object -First 3) })
}

$languages = New-Object System.Collections.Generic.List[object]
foreach ($s in $signalLang) { $languages.Add($s) }
foreach ($lang in ($languageEvidence.Keys | Sort-Object)) {
	if (-not ($languages | Where-Object { $_.name -eq $lang })) {
		$languages.Add(@{ name = $lang; confidence = "medium"; evidence_paths = @($languageEvidence[$lang] | Sort-Object) })
	}
}

# Monorepo heuristic: multiple manifests of same type in distinct directories
$monorepo = $false
foreach ($pattern in @("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml")) {
	$paths = @($allFiles | Where-Object { $_.Name -eq $pattern } | ForEach-Object { Split-Path -Parent $_.FullName } | Sort-Object -Unique)
	if ($paths.Count -gt 1) { $monorepo = $true }
}

$unknowns = @()
if (-not $ciPresent) {
	# Not an error; explicit unknown permitted
	$unknowns += "CI presence not detected (may be absent or non-standard)."
}
$unknowns += "Canonical verification command unknown unless declared in repo signals."

$readmePaths = @()
foreach ($r in @($readmes)) {
	$readmePaths += (Rel $r.FullName)
}

$policyPaths = @()
foreach ($d in @($policy)) {
	$policyPaths += (Rel $d.FullName)
}

$profileGeneratedAt = New-IsoTimestampUtc

$languagesArr = $languages.ToArray()
$depManagersArr = $depManagers.ToArray()
$ciDefsArr = @($ciDefs.ToArray() | Sort-Object)
$containerDefsArr = @($containerDefs.ToArray() | Sort-Object)
$automationPathsArr = @($automationPaths.ToArray() | Sort-Object)

$profile = [ordered]@{
	schema_version = "1.0"
	generated_at   = $profileGeneratedAt
	repo_root      = "."
	signals        = [ordered]@{
		readme_paths = @($readmePaths)
		policy_paths = @($policyPaths)
		monorepo     = $monorepo
	}
	detections     = [ordered]@{
		languages           = $languagesArr
		dependency_managers = $depManagersArr
		ci                  = [ordered]@{ present = $ciPresent; definition_paths = $ciDefsArr }
		containers          = [ordered]@{ present = $containersPresent; definition_paths = $containerDefsArr }
		runtime_clues       = [ordered]@{ version_pin_paths = @($versionPins); env_template_paths = @($envTemplates); automation_paths = $automationPathsArr }
	}
	constraints    = [ordered]@{ protected_paths = @(); required_confirmations = @(); notes = @() }
	unknowns       = @($unknowns)
	evidence       = @()
}

foreach ($p in @($profile.signals.readme_paths)) {
	$profile.evidence += [ordered]@{ type = "file_presence"; path = $p; observed = $true; observed_at = New-IsoTimestampUtc }
}
foreach ($p in @($profile.signals.policy_paths)) {
	$profile.evidence += [ordered]@{ type = "file_presence"; path = $p; observed = $true; observed_at = New-IsoTimestampUtc }
}

$profilePath = Join-Path $GovDir "project-profile.json"
Write-TextFile -Path $profilePath -Content (Json-Line $profile)
Track-Created $profilePath

Add-Evidence -Phase "phase-1" -Action "project_interrogation" -Input @{ file_count = $allFiles.Count } -Result @{ readmes = @($profile.signals.readme_paths); ci_present = $ciPresent; containers_present = $containersPresent; dependency_managers = @($depManagers | ForEach-Object { $_.name }) } -Law "LAW 1" -Source "repo_scan"

# -------------------------
# Phase 2 — Environment Discovery
# -------------------------
if (-not $DryRun) {
	Ensure-Dir $EvidenceDir
	if (-not (Test-Path -LiteralPath $EvidenceFile)) {
		New-Item -ItemType File -Path $EvidenceFile | Out-Null
		Track-Created $EvidenceFile
	}
	$EvidenceReady = $true
	foreach ($e in $BufferedEvidence) {
		Add-Content -LiteralPath $EvidenceFile -Value (Json-Line $e)
	}
	$BufferedEvidence.Clear() | Out-Null
}

Add-Evidence -Phase "phase-2" -Action "environment_discovery" -Input @{ os = $env:OS; pwsh_version = $PSVersionTable.PSVersion.ToString() } -Result @{ evidence_store = (Rel $EvidenceFile); writable = (-not $DryRun) } -Source "execution_layer" -Law "LAW 1"

# -------------------------
# Phase 3 — System Manifest Creation
# -------------------------
$govVersionSrc = Get-Content -LiteralPath $SourceFiles["governance_version"] -Raw | ConvertFrom-Json
$govVersionDst = Join-Path $GovDir "governance-version.json"
Copy-File -Source $SourceFiles["governance_version"] -Dest $govVersionDst
Track-Created $govVersionDst

$manifest = [ordered]@{
	schema_version     = "1.0"
	generated_at       = New-IsoTimestampUtc
	governance_version = $govVersionSrc
	project_identity   = [ordered]@{ name = (Split-Path -Leaf $TargetFull); repo_root = "." }
	detections         = [ordered]@{
		languages              = @($languages | ForEach-Object { $_.name })
		dependency_managers    = @($depManagers | ForEach-Object { $_.name })
		ci_definition_paths    = @($ciDefs | Sort-Object)
		container_definition_paths = @($containerDefs | Sort-Object)
	}
	entrypoints        = [ordered]@{ paths = @(); commands = @(); interfaces = @(); evidence_paths = @($profile.signals.readme_paths) }
	automation_signals = [ordered]@{ ci_present = $ciPresent; automation_paths = @($automationPaths | Sort-Object) }
	verification_hooks = [ordered]@{
		doctor_checks = @(
			[ordered]@{
				id = "doctor-command-executable"
				pattern_id = "PAT-005-command-executable"
				description = "Validate that any declared verification commands discovered from repo signals are executable (help/version/dry-run when possible)."
				inputs = $null
				success_criteria_notes = "Only validate commands discovered from repo state or explicitly provided; do not invent commands."
			},
			[ordered]@{
				id = "doctor-configuration-valid"
				pattern_id = "PAT-003-configuration-valid"
				description = "Validate that required configuration referenced by docs/CI/manifest exists and is syntactically valid."
				inputs = $null
				success_criteria_notes = "Prefer in-repo validators when present; otherwise perform minimal format validation."
			}
		)
		commands = @()
	}
	constraints        = [ordered]@{ protected_paths = @(); notes = @() }
	unknowns           = @($unknowns)
}

$manifestPath = Join-Path $GovDir "system-manifest.json"
Write-TextFile -Path $manifestPath -Content (Json-Line $manifest)
Track-Created $manifestPath

Add-Evidence -Phase "phase-3" -Action "system_manifest_created" -Input @{ profile = (Rel $profilePath) } -Result @{ manifest = (Rel $manifestPath); governance_version = $govVersionSrc.version } -Source "execution_layer" -Law "LAW 4"

# -------------------------
# Phase 4 — Guardrail Installation
# -------------------------
$guardrailsDst = Join-Path $GovDir "guardrails\baseline-rules.yaml"
$patternsDst = Join-Path $GovDir "guardrails\validation-patterns.yaml"
Copy-File -Source $SourceFiles["guardrails"] -Dest $guardrailsDst
Copy-File -Source $SourceFiles["validation_patterns"] -Dest $patternsDst
Track-Created $guardrailsDst
Track-Created $patternsDst

Add-Evidence -Phase "phase-4" -Action "guardrails_vendored" -Input @{ sources = @("guardrails/baseline-rules.yaml", "guardrails/validation-patterns.yaml") } -Result @{ installed = @((Rel $guardrailsDst), (Rel $patternsDst)) } -Source "execution_layer" -Law "LAW 2"

# -------------------------
# Phase 5 — Task Governance Activation
# -------------------------
$capRegDst = Join-Path $GovDir "capability-registry.md"
$sessionStartDst = Join-Path $GovDir "session-start.md"
$evidenceSpecDst = Join-Path $GovDir "evidence-spec.md"

Copy-File -Source $SourceFiles["capability_registry"] -Dest $capRegDst
Copy-File -Source $SourceFiles["session_start"] -Dest $sessionStartDst
Copy-File -Source $SourceFiles["evidence_spec"] -Dest $evidenceSpecDst
Track-Created $capRegDst
Track-Created $sessionStartDst
Track-Created $evidenceSpecDst

$agentRuntimePath = Join-Path $GovDir "agent-runtime.md"
$agentRuntime = @(
	'# Agent Runtime Governance (Project-Local)',
	'',
	'This file activates governed execution for AI agents within this repository.',
	'It is generated by governance bootstrap and must be kept within `.governance/`.',
	'',
	'## Mandatory Lifecycle',
	'Interrogate -> Validate -> Plan -> Execute -> Verify -> Learn',
	'',
	'## Session Start',
	'Agents must follow the project-local session start contract: `.governance/session-start.md`.',
	'',
	'## Guardrails and Validation Patterns',
	'- Guardrails: `.governance/guardrails/baseline-rules.yaml`',
	'- Validation patterns: `.governance/guardrails/validation-patterns.yaml`',
	'',
	'## Evidence Requirements',
	'Evidence must be recorded in files (not chat) under `.governance/evidence/` using `.governance/evidence-spec.md`.',
	'',
	'## Refusal Criteria',
	'Agents must refuse or stop when:',
	'- requested action violates guardrails',
	'- action is destructive and explicit confirmation is not provided',
	'- completion is requested but verification evidence cannot be produced',
	'- stack assumptions would be introduced',
	'',
	'## Project Manifests',
	'- Project profile: `.governance/project-profile.json`',
	'- System manifest: `.governance/system-manifest.json`'
) -join "`n"

Write-TextFile -Path $agentRuntimePath -Content $agentRuntime
Track-Created $agentRuntimePath

Add-Evidence -Phase "phase-5" -Action "runtime_activated" -Input @{ } -Result @{ vendored = @((Rel $capRegDst), (Rel $sessionStartDst), (Rel $evidenceSpecDst), (Rel $agentRuntimePath)) } -Source "execution_layer" -Law "LAW 2"

# -------------------------
# Phase 6 — Learning System Initialization
# -------------------------
$incDir = Join-Path $GovDir "learning\incidents"
$propDir = Join-Path $GovDir "learning\proposals"
Ensure-Dir $incDir
Ensure-Dir $propDir
if (-not $DryRun) {
	Track-Created $incDir
	Track-Created $propDir
}

$learningReadmePath = Join-Path $GovDir "learning\README.md"
$learningReadme = @(
	'# Governance Learning (Controlled Evolution)',
	'',
	'Lifecycle (required): Incident -> Analysis -> Guardrail Proposal -> Human Approval -> Governance Update.',
	'',
	'Records:',
	'- Incidents: `.governance/learning/incidents/`',
	'- Proposals: `.governance/learning/proposals/`',
	'',
	'Explicit prohibition: agents must never auto-mutate governance rules or validation patterns.'
) -join "`n"
Write-TextFile -Path $learningReadmePath -Content $learningReadme
Track-Created $learningReadmePath

Add-Evidence -Phase "phase-6" -Action "learning_initialized" -Input @{ } -Result @{ learning_paths = @((Rel $incDir), (Rel $propDir), (Rel $learningReadmePath)) } -Source "execution_layer" -Law "LAW 6"

# -------------------------
# Phase 7 — Governance Status Report
# -------------------------
$statusPath = Join-Path $GovDir "status.md"
$createdSorted = @($CreatedPaths | Sort-Object)
$status = @(
	"# Governance Status Report",
	"",
	"- Session: $SessionId",
	"- Timestamp (UTC): $(New-IsoTimestampUtc)",
	"- Governance version source: ../governance-version.json",
	"",
	"## Created Governance Artifacts",
	($createdSorted | ForEach-Object { "- $($_)" }),
	"",
	"## Interrogation Summary",
	"- Readmes: $($profile.signals.readme_paths.Count)",
	"- Policy docs: $($profile.signals.policy_paths.Count)",
	"- CI detected: $ciPresent",
	"- Containers detected: $containersPresent",
	"",
	"## Environment Discovery Summary",
	"- Evidence store: $(Rel $EvidenceFile)",
	"- Dry-run: $([bool]$DryRun)",
	"",
	"## Evidence Summary",
	"Evidence is recorded in: $(Rel $EvidenceFile)",
	"",
	"## Non-Negotiable Statement",
	"No application code was modified during bootstrap."
) -join "`n"
Write-TextFile -Path $statusPath -Content $status
Track-Created $statusPath

Add-Evidence -Phase "phase-7" -Action "status_report_created" -Input @{ } -Result @{ status = (Rel $statusPath); no_app_code_modified = $true } -Source "execution_layer" -Law "LAW 2"

Write-Info "Done."
if ($DryRun) {
	Write-Info "(DRY-RUN) No files written."
}
