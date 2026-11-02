# DraftRec: gaps for pricing Worlds semis and finals

**Source under review:** Lee, Hwang, Kim, Lee & Choo, *DraftRec: Personalized Draft
Recommendation for Winning in Multi-Player Online Battle Arena Games*, WWW '22,
[arXiv 2204.12750](https://arxiv.org/abs/2204.12750).

**Use case:** pricing Kalshi LoL Worlds knockout contracts (`KXLOLGAME` series winner,
`KXLOLMAP` per map, `KXLOLSCORE` exact score, `KXLOLTOTALMAPS`) for the semifinals and the
final. All are Bo5 with Fearless draft. The pricer is `lolprice.py` (outside this repo):

```
logit p_k = mu + eta + side_adv * s_k + fearless_drift * (k - 1),   eta ~ N(0, sigma^2) per series
```

It solves the series exactly with a DP over (wins_A, wins_B, picker), integrated over `eta`
with Gauss–Hermite quadrature.

**TL;DR:** DraftRec is a solo-queue champion **recommender**. Its win-probability head is
a by-product, near coin-flip quality, and never checked for calibration. It can't supply
`p_map`, `sigma` or `side_adv`. The most it could do is inform `fearless_drift` through its
champion-pool embeddings, and even that needs pro data it doesn't use. The three papers
below cover what's missing.

---

## 1. What the paper measures

| Item | Value | Where |
|---|---|---|
| LoL data | 279,893 matches, 62,466 players, 156 champions | Table 1 |
| Population | Top 0.1% **ranked solo queue**, 2021-06-01 to 2021-09-09 | §5.1 |
| Split | Time-ordered 85 / 5 / 10 train / val / test | §5.1 |
| Task 1 | Predict the champion a player picks at each draft turn | §3.2, Eq. 4 |
| Task 2 | Predict match outcome `v̂_t` at each draft turn (a by-product head) | Eq. 13 |
| Loss | `λ·L_p + (1−λ)·L_v + c‖θ‖²`, with **λ = 0.1** for LoL | Eq. 15, Table 8 |

Outcome prediction, LoL test set:

| Model | ACC (mid-draft) | MAE (mid-draft) | ACC (post-draft) | MAE (post-draft) |
|---|---|---|---|---|
| Majority class | 0.5040 | 0.4960 | 0.5040 | 0.4960 |
| Logistic regression | 0.5255 | 0.4973 | 0.5323 | 0.4975 |
| OptMatch | 0.5411 | 0.4944 | 0.5449 | 0.4928 |
| DraftRec-no-history | 0.5284 | 0.4942 | 0.5432 | 0.4893 |
| **DraftRec** | **0.5535** | **0.4842** | **0.5618** | **0.4826** |

Mid-draft numbers are from Table 3, post-draft from Table 9 (Appendix B.1).

Recommendation strategy (Table 4): `DraftRec_{p+v}` reaches a **Win@3 of 54.12%**. That
"win rate" is **predicted by a second model** (OptMatch), not observed (§5.5).

## 2. Gaps for Bo5 pricing

| # | Gap | Evidence | Why it matters for semis and finals |
|---|---|---|---|
| G1 | **Wrong population.** Solo-queue players get random turns and roles, while pro drafts are run by a team and coach with a fixed side and first pick | §3.1: "Each player is randomly assigned a particular turn"; data is top 0.1% ranked (§5.1) | Worlds knockouts are 5-stacks with scrim prep. Synergy learned from solo queue doesn't carry over to pro drafting |
| G2 | **Wrong draft format.** It models one ban phase, then picks 1-2-2-2-2-1 | §3.1, Fig. 1 | Pro drafts have two ban phases with picks between them, and Fearless (added after the paper) removes champions across games. The paper has no idea of game *k* in a series |
| G3 | **No team strength.** The only inputs are each player's own champion history and in-game stats | §4.1, Eq. 1; "Avg. Match History 66.38" (Table 1) | At Worlds, team strength (`mu`) is the main driver. Draft effects are second order |
| G4 | **Weak signal.** Post-draft ACC is 0.5618 against a majority-class baseline of 0.5040 | Table 9 | MAE 0.4826 means predictions sit near 0.5. As a `p_map` input it adds almost nothing |
| G5 | **No calibration or proper scoring.** Only ACC and MAE are reported, with no log-loss, Brier or reliability curve | §5.2 "Evaluation" | Pricing needs calibrated probabilities. MAE rewards being pulled toward 0.5 and doesn't reward correct probabilities |
| G6 | **Outcome head barely weighted.** λ = 0.1 puts 90% of the loss on champion prediction | Table 8 | `v̂` is a side product of a recommender, not a fitted win-probability model |
| G7 | **"Win rate" from a second model.** Win@3 is OptMatch's prediction, not realized results | §5.5 | Not evidence that its draft advice changes win odds |
| G8 | **Single game.** No series state, side selection, or game-to-game correlation | Whole paper | Bo5 contracts depend on game-to-game correlation (`sigma`) and the side rule. Neither appears |
| G9 | **Stale patch window.** About 3 months of 2021 patches, one time-ordered split, no walk-forward | §5.1 | Worlds 2026 runs on a different patch and champion pool. Drift isn't measured |
| G10 | **Extra complexity doesn't always pay.** On Dota 2 post-draft, LR (0.6126) beats DraftRec (0.6110) | Table 9, App. B.1 | A small, well-calibrated model is a reasonable default (see §3.1) |
| G11 | **No market comparison.** Results are only compared with other ML models | Whole paper | It's unknown whether any of this signal is already in prices |
| G12 | **Gap the authors acknowledge.** In-game features ignore the other players in the match | §6, "Conclusion" | Player form is measured in isolation from opponents |

**Possibly useful part (my proposal, not a claim the paper makes).** The player network
learns each player's distribution over champions, and history length matters up to about
L = 50 (App. B.2, Fig. 6). Under Fearless, a team's edge late in a series depends on how
deep its champion pools are. So an entropy-style pool-depth score per player, fit on **pro**
data, could set the sign and size of `fearless_drift`. The paper doesn't test this, and
its solo-queue embeddings would have to be refit.

## 3. Three papers that fill the gaps

### 3.1 Guan & Tung (2026): pro map model benchmarked against Polymarket

*Pre-game paired-comparison modeling of professional League of Legends map outcomes*,
[arXiv 2609.08060](https://arxiv.org/abs/2609.08060) (stat.AP).

- **Model:** logistic `p_i = expit(β0 + γ_FP·1[blue first-pick] + β_B·E_b − β_R·E_r + θ_b − θ_r)`
  (Eq. 6–7). `E` is an EWMA of each team's past results on the same side, and `θ` is a
  ridge-shrunk stable team strength.
- **Data:** 5,135 pro maps across six leagues and three international events, 2024–2026
  (Table 2, with 190 Worlds games).
- **Calibration:** walk-forward calibration slope 0.995 (abstract). Brier is 0.2207
  walk-forward and 0.2230 on the global holdout, against 0.2351 for dynamic Bradley–Terry.
- **Against Polymarket (Table 7, n = 924):** level on per-game contracts (Δ = +0.006, 95% CI
  −0.002 to +0.015). On **Worlds** the market is clearly better: **Δ = +0.069, t = +4.61,
  n = 50**, the only league that survives Bonferroni. The market is also modestly better
  on series deciders.

**Fills:** G1, G3, G4, G5, G9 and G11. It gives a calibrated, pro-only `p_map` with a
first-pick term (which maps to `side_adv`), plus a market benchmark.

**Pricing impact:** it is the natural source for `p_map`. Its Worlds result is the warning
that matters most here, though. Cross-region strength transfer is where a pure stats model
does worst against the market, so for Worlds semis and finals **shrink the model toward the
market mid** rather than trading against it. The paper also leaves a **series-level** model
as future work (§4.3, §6), which is what `lolprice.py`'s DP covers.

### 3.2 Ferrall & Smith (1999): sequential game model of best-of-n series

*A Sequential Game Model of Sports Championship Series: Theory and Estimation*, *Review of
Economics and Statistics* 81(4):704–719, [doi:10.1162/003465399558427](https://doi.org/10.1162/003465399558427)
([working paper PDF](https://ageconsearch.umn.edu/record/273379/files/qed_wp_945.pdf)).

- **Approach:** solves the subgame-perfect equilibrium of a best-of-n series and nests a
  model where teams "do not respond to the state of the series". Fit on World Series,
  Stanley Cup and NBA Finals data.
- **Findings:** strategic effects are **negligible** in all three sports. Unobserved
  heterogeneity is also negligible once regular-season record and finals experience are
  controlled for: "teams are estimated to be exactly as strong as they appear on paper".
- **Mechanism:** "uncontrolled differences in the strengths of the teams induce positive
  serial correlation", which can be "mistaken for dependence of outcomes on the state of
  the series." For example, 87% of World Series that reach 3–0 end in four games.

**Fills:** G8. It justifies a DP in which each game's probability depends only on strength
and side (no "back against the wall" term). It also gives a clear reading of `sigma`: it is
the strength the model can't observe. That shrinks as the strength model improves.

**Pricing impact:** the backtest in `lolprice` finds σ ≈ 0.75 with market-implied `p` (0.5 for
semis and finals pooled), and no momentum beyond the scoreline. That is consistent with this
paper's results. **Implication:** if `p_map` comes from §3.1 rather than a rough prior,
**re-fit σ downward**. Leaving σ at 0.75 would double-count uncertainty and push 3-0 and
3-2 prices too close together. Caveat: the paper covers stick-and-ball sports, so "home
field" stands in for side selection only by analogy.

### 3.3 Hodge et al. (2021): live win prediction for pro esports

*Win Prediction in Multi-Player Esports: Live Professional Match Prediction*, *IEEE
Transactions on Games* 13(4):368–379, [doi:10.1109/TG.2019.2948469](https://doi.org/10.1109/TG.2019.2948469)
([accepted manuscript](https://eprints.whiterose.ac.uk/152931/)).

- **Data:** 5,744 Dota 2 replays (23.97% professional), plus 186 TI 2017 pro replays used in
  a live tournament trial.
- **Results:** "up to 85% accurate after 5 minutes of gameplay". Between 5 and 20 minutes,
  accuracy stays in a 70–80% band.
- **Method:** high-MMR public games stand in for scarce pro data. Patch changes can make
  older data unusable.

**Fills:** in-game and between-game repricing, which DraftRec doesn't address and
Guan & Tung rule out of scope (§6).

**Pricing impact:** `lolprice --history "W-2,L+1"` treats gold difference at 15 minutes as a
noisy reading of strength. It uses **assumed** values of `gd_per_logit = 1.0k` and
`gd_sd = 2.5k`. This paper is the template for fitting those two numbers on pro games.
Kalshi map markets trade during play, so the same approach gives a live fair value for each
map. Caveat: Dota 2 isn't LoL, so the feature set carries over but the coefficients don't.

## 4. Critique

**Of DraftRec, as a pricing source:**

1. **Headline vs. substance.** The "state-of-the-art outcome prediction" claim rests on
   +2.3% accuracy over 0.54 (Table 3), with no uncertainty on calibration. That is
   significant (p < 0.01) only because the test set is large. Economically it's close to
   nothing.
2. **MAE is the wrong metric.** For a binary outcome, MAE is minimized by predicting the
   median class rather than the true probability, so it rewards overconfidence. A pricing
   model needs log-loss or Brier plus a reliability plot. Without those, `v̂` can't be
   turned into a probability.
3. **The win-rate evaluation scores itself with a model.** Win@3 = 54.12% is OptMatch's
   opinion of DraftRec's drafts. Both models learn the same solo-queue patterns, so they
   can share the same biases. The paper raises this concern itself (§5.5, citing [45]) but
   only partly addresses it by switching models.
4. **The user study measures how users feel, not outcomes.** 84 respondents (Table 5) said
   they found the picks familiar and convincing. That says nothing about win probability.
5. **Fine as a recommender.** Champion recommendation is strong: HR@10 is 0.8836 against
   0.8547 for SASRec (Table 2). The paper does what it set out to do. It just isn't a
   pricing paper.

**Of the replacements:**

- Guan & Tung is pro-only and market-benchmarked, but it covers **Bo3 maps** and only
  **50 Worlds maps**. Its Worlds result is the one most relevant here, and also the one with
  the most uncertainty. It's a single preprint not yet peer reviewed (stat.AP, Sep 2026).
- Ferrall & Smith is from 1999 and covers other sports. It helps with model structure (no
  state dependence, σ as unobserved strength), not with LoL parameters.
- Hodge et al. covers Dota 2 and in-game prediction only. It reports accuracy rather than
  calibration, so it has the same metric weakness as DraftRec (point 2 above).

## 5. Mapping onto `lolprice.py`

| Param | Current source | Proposed source | Paper |
|---|---|---|---|
| `p_map` | Prior or `--fit` to Kalshi mids | Ridge-BT + EWMA map model fit on pro data, **shrunk toward the market at Worlds** | Guan & Tung, Table 7 |
| `side_adv` | Assumed (0 to 0.25 in sensitivity runs) | `γ_FP` first-pick coefficient refit on side-select games | Guan & Tung, Eq. 6 |
| `sigma` | Backtest σ ≈ 0.75 (0.5 for semis and finals) | Refit **conditional on** the new `p_map`; expect it to shrink | Ferrall & Smith |
| `fearless_drift` | Assumed | Champion-pool depth score from pro histories (untested proposal) | DraftRec §4.1 (bridge, untested) |
| `gd_per_logit`, `gd_sd` | Assumed 1.0k, 2.5k | Fit on pro games' 15-minute state | Hodge et al. |
| State dependence | None beyond the scoreline (the backtest found none) | Keep none | Ferrall & Smith; `lolprice` backtest |

**Semis and finals context from the `lolprice` backtest** (non-Worlds, 33 events). Finals
favourites were priced at 0.69 and won **0.81** (n = 32). Semis had **32%** upsets and 29%
3-0s (n = 65). The reaction after game 1 was well calibrated: the game-1 winner was priced
at 0.733 and won 0.753. None of these edges is reliable after fees. Use them as pricing
priors, not a strategy.

## 6. Open questions

- **Data source:** none of the three papers publishes a pro LoL dataset this pipeline can
  pull. Leaguepedia rate-limits it, and the Oracle's Elixir CSVs moved. TBD.
- **Fearless:** no paper measures the Fearless effect on late-series maps. That needs its
  own estimate from 2025–2026 Bo5s.
- **Proper series-level scoring:** Guan & Tung suggest an RPS over the ordered `KXLOLSCORE`
  outcomes. Use it to evaluate the DP against Kalshi on exact-score contracts.
