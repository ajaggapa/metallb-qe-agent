# Detailed Test Plan: [Feature Name] ([JIRA_KEY])

## JIRA Reference

- Ticket Key: `[JIRA_KEY]`
- Ticket URL: [https://issues.redhat.com/browse/JIRA_KEY or your tracker URL]

## Related High-Level Test Plan

- Link or summary: [Google Doc URL to high-level plan, or "Derived from Epic only"]

## Prerequisites and Environment

- OpenShift/Kubernetes version:
- MetalLB / metallb-operator / frr-k8s versions (if known):
- Default CLI: `oc` (use `kubectl` where equivalent)
- MetalLB namespace for this plan: `metallb-system` (change here only if the Epic targets a different layout)
- Assumptions (network, workers, privileged FRR, etc.):

## Placeholders

Intro sentence: all names below are **fixed literals** for this plan (no `METALLB_NS`-style variables). Group by theme so the section stays scannable in Google Docs.

**Namespace**

- MetalLB: `metallb-system`

**Baseline pool (TC-01)**

- IPAddressPool: `cnf20333-baseline-pool`
- L2Advertisement: `cnf20333-baseline-l2`
- CIDR: `192.0.2.0/24` (documentation range; pick another non-overlapping CIDR only if this conflicts with your lab)

**Other test objects**

- Add one bullet per manifest name (peer, secret, ConfigMap, etc.).

## Detailed Test Cases

### TC-01: [Name aligned with high-level TC-01]

**Purpose:** [Same intent as high-level Purpose]

**Pass/Fail criteria (summary):** [Short reminder from high-level plan]

#### Step 1 — [Short title]

Run:

```bash
oc get crd configurationstates.metallb.io -o name
```

Expected: [What the tester should see]

#### Step 2 — [Short title]

Manifest (YAML):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cnf20333-example
  namespace: metallb-system
data:
  key: value
```

Run:

```bash
oc apply -f step2-manifest.yaml
oc describe configmap cnf20333-example -n metallb-system
```

Expected: [What the tester should see]

Cleanup (optional):

```bash
oc delete configmap cnf20333-example -n metallb-system --ignore-not-found
```

### TC-02: [Name]

**Purpose:**

**Pass/Fail criteria (summary):**

#### Step 1 — [...]

Manifest (YAML):

```yaml
# ...
```

Run:

```bash
oc get nodes
```

Expected:

### TC-03: [Name]

**Purpose:**

**Pass/Fail criteria (summary):**

#### Step 1 — [...]

Manifest (YAML):

```yaml
# ...
```

Run:

```bash
oc version --client
```

Expected:

## References

1. [Jira / design doc / PR links]
