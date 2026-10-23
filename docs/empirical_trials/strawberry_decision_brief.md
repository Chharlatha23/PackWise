# Strawberry Postharvest Endpoint Decision Brief

## 1. Context and Objective
This brief is prepared for domain-expert review to establish a defensible, operational shelf-life endpoint for strawberry (*Fragaria × ananassa*) postharvest packaging trials. The AI-Food-Packaging-Optimizer strictly requires an explicit, protocol-specific endpoint definition to evaluate empirical trial outcomes.

## 2. Physiological and Pathological Considerations
Strawberries are highly perishable, non-climacteric fruits characterized by high respiration rates and susceptibility to mechanical injury and fungal infection. Shelf life is predominantly limited by two factors:
*   **Pathological Decay:** Often caused by *Botrytis cinerea* (gray mold).
*   **Physiological Deterioration:** Characterized by rapid water loss, leading to shriveling and softening.

## 3. Literature-Derived Thresholds
*   **Weight Loss / Shriveling:** A commonly cited benchmark for maximum allowable weight loss before visible shriveling and loss of marketability occurs is **~6%** [1][2].
*   **Visible Decay:** Retail and market acceptability standards typically enforce a near-zero tolerance for visible decay (e.g., nesting mold). Some research protocols define the endpoint as **>0% to 5% visible decay incidence** within a replicate batch [1][3].
*   **Firmness:** While softening is a major issue, critical firmness limits are highly cultivar-specific and require destructive penetration tests (e.g., using a penetrometer or texture analyzer) [3].

## 4. Candidate Endpoint Options for Expert Review

The following operational endpoint definitions are submitted for domain-expert approval. **Only one primary endpoint (or a defined composite) may be selected for the trial protocol.**

### Option A: Critical Weight Loss
*   **Definition:** `cumulative_weight_loss > 6.0%`
*   **Evidence Needed:** Expert confirmation that 6% accurately reflects the shriveling limit for the specific selected cultivar under the planned storage conditions.

### Option B: Visible Decay Threshold
*   **Definition:** `decay_incidence > 5.0%` (or alternative strictly defined % of berries showing visible mold).
*   **Evidence Needed:** Expert justification for the chosen percentage (e.g., differentiating between a commercial retail standard vs. an academic research endpoint). 

### Option C: Composite Sensorial/Physical Limit
*   **Definition:** `overall_acceptability_score < 3.0` (on a 1-5 scale evaluated by trained panelists) OR `weight_loss > 6.0%`.
*   **Evidence Needed:** A standardized sensory rubric and a panel trained to evaluate the specific cultivar.

## 5. References
*   [1] Kader, A. A. (2002). Postharvest Technology of Horticultural Crops. University of California Agriculture and Natural Resources.
*   [2] Nunes, M. C. N., et al. (1998). "Temperature abuse limits the quality of strawberries." *Journal of the American Society for Horticultural Science*.
*   [3] Mitcham, E. J., et al. (1996). "Quality of 'Chandler' strawberries." *Postharvest Biology and Technology*.

*(Note: Citations are representative of standard postharvest physiology references and provided for expert verification. They do not constitute project-collected empirical data.)*
