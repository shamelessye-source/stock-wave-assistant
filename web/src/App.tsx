import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import { apiGet, apiPost, apiPut } from "./api/client";
import type { ApiResult } from "./api/client";

type LoadState = "idle" | "loading" | "ready" | "error";
type TabId =
  | "overview"
  | "indicators"
  | "risk"
  | "wave"
  | "ledger"
  | "report"
  | "settings";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "overview", label: "总览" },
  { id: "indicators", label: "自选股指标" },
  { id: "risk", label: "组合风控" },
  { id: "wave", label: "波段状态" },
  { id: "ledger", label: "交易台账" },
  { id: "report", label: "14:55 报告" },
  { id: "settings", label: "设置/自检" },
];

type HealthResponse = {
  status: string;
  service: string;
  mode: string;
};

type ConfigStatus = {
  status: string;
  mode: string;
  providers: {
    market: string;
    llm: string;
  };
  codex: {
    enabled: boolean;
    model: string;
    timeout_seconds: number;
    sandbox_mode: string;
    cli_path_configured: boolean;
    cli_path_exists: boolean;
    version_check: string;
  };
  database: {
    engine: string;
    configured: boolean;
  };
};

type WatchlistItem = {
  name: string;
  symbol: string;
  market: string;
  group: string;
  theme: string;
  enabled: boolean;
  observation_note: string;
  risk_note: string;
};

type WatchlistResponse = {
  version: number;
  items: WatchlistItem[];
};

type WatchlistValidation = {
  valid: boolean;
  errors: string[];
};

type IndicatorValues = {
  ma20: number | null;
  ma60: number | null;
  momentum_5d_pct: number | null;
  momentum_10d_pct: number | null;
  momentum_20d_pct: number | null;
  max_drawdown_pct: number | null;
  atr_pct: number | null;
  volume_ratio: number | null;
};

type IndicatorRow = {
  name: string;
  symbol: string;
  latest_trade_date: string | null;
  latest_close: number | null;
  indicators: IndicatorValues;
  data_status: string;
  degradation_reasons: string[];
};

type IndicatorResponse = {
  provider: string;
  items: IndicatorRow[];
};

type TradeSide = "increase_position" | "decrease_position";

type TradeRecord = {
  id: number;
  instrument_name: string;
  instrument_code: string;
  trade_date: string;
  side: TradeSide;
  quantity: string;
  price: string;
  fee: string;
  note: string;
  created_at: string;
};

type TradeForm = {
  instrument_name: string;
  instrument_code: string;
  trade_date: string;
  side: TradeSide;
  quantity: string;
  price: string;
  fee: string;
  note: string;
};

type TradeResponse = {
  items: TradeRecord[];
};

type PnlItem = {
  instrument_name: string;
  instrument_code: string;
  quantity: string;
  average_cost: string;
  cumulative_fee: string;
  realized_pnl: string;
  current_market_value: string | null;
  unrealized_pnl: string | null;
  total_pnl: string;
  status: string;
  errors: string[];
};

type PnlResponse = {
  items: PnlItem[];
};

type RiskPosition = {
  instrument_name: string;
  instrument_code: string;
  group: string;
  direction: string;
  market_value: string;
  position_weight_pct: string;
  unrealized_pnl: string;
  realized_pnl: string;
  total_pnl: string;
  risk_status: string;
  reasons: string[];
};

type ConcentrationItem = {
  name: string;
  market_value: string;
  weight_pct: string;
  risk_status: string;
};

type RiskSummary = {
  total_market_value: string;
  floating_pnl: string;
  realized_pnl: string;
  total_pnl: string;
  max_single_position: RiskPosition;
  max_single_position_risk_status: string;
  direction_concentration: ConcentrationItem[];
  group_concentration: ConcentrationItem[];
  positions: RiskPosition[];
  data_status: string;
  degradation_reasons: string[];
};

type WaveStateItem = {
  name: string;
  symbol: string;
  latest_trade_date: string | null;
  data_status: string;
  indicator_summary: IndicatorValues & {
    latest_close: number | null;
  };
  position_summary: {
    quantity: string;
    current_market_value: string | null;
    total_pnl: string;
    status: string;
  };
  risk_summary: {
    position_weight_pct: string;
    risk_status: string;
    reasons: string[];
  };
  wave_state: {
    state: string;
    label_cn: string;
    total_score: string;
    reasons: string[];
  };
};

type WaveStatesResponse = {
  items: WaveStateItem[];
};

type ReportListItem = {
  name: string;
  symbol: string;
  state: string;
  label_cn: string;
  total_score: string;
  reasons: string[];
  data_status: string;
  position_weight_pct: string;
};

type PrecloseReport = {
  report_type: string;
  report_status: string;
  as_of_date: string;
  as_of_time: string;
  market_session_status: {
    status: string;
    session: string;
    calendar_mode: string;
    is_trading_day: boolean;
    is_preclose_time: boolean;
  };
  not_advice: boolean;
  data_status: string;
  portfolio_summary: {
    total_market_value: string;
    floating_pnl: string;
    realized_pnl: string;
    total_pnl: string;
    max_single_position_weight_pct: string;
    max_single_position_risk_status: string;
    data_status: string;
  };
  risk_flags: string[];
  watchlist_rankings: ReportListItem[];
  state_distribution: Record<string, number>;
  attention_items: ReportListItem[];
  rotation_watch_candidates: ReportListItem[];
  position_review_candidates: ReportListItem[];
  data_quality_notes: string[];
  generated_at: string;
};

type ReportExplanation = {
  success: boolean;
  provider: string;
  model: string;
  duration_ms: number;
  text: string;
  error: string | null;
  exit_code: number | null;
};

const emptyRiskSummary: RiskSummary = {
  total_market_value: "0.00",
  floating_pnl: "0.00",
  realized_pnl: "0.00",
  total_pnl: "0.00",
  max_single_position: {
    instrument_name: "",
    instrument_code: "",
    group: "",
    direction: "",
    market_value: "0.00",
    position_weight_pct: "0.00",
    unrealized_pnl: "0.00",
    realized_pnl: "0.00",
    total_pnl: "0.00",
    risk_status: "data_insufficient",
    reasons: [],
  },
  max_single_position_risk_status: "data_insufficient",
  direction_concentration: [],
  group_concentration: [],
  positions: [],
  data_status: "data_insufficient",
  degradation_reasons: [],
};

const emptyTradeForm: TradeForm = {
  instrument_name: "",
  instrument_code: "",
  trade_date: todayString(),
  side: "increase_position",
  quantity: "",
  price: "",
  fee: "0",
  note: "",
};

const emptyWatchlistItem: WatchlistItem = {
  name: "",
  symbol: "",
  market: "",
  group: "",
  theme: "",
  enabled: true,
  observation_note: "",
  risk_note: "",
};

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [config, setConfig] = useState<ConfigStatus | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistResponse>({
    version: 1,
    items: [],
  });
  const [indicatorProvider, setIndicatorProvider] = useState("mock");
  const [indicators, setIndicators] = useState<IndicatorRow[]>([]);
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [pnlItems, setPnlItems] = useState<PnlItem[]>([]);
  const [riskSummary, setRiskSummary] = useState<RiskSummary>(emptyRiskSummary);
  const [waveStates, setWaveStates] = useState<WaveStateItem[]>([]);
  const [precloseReport, setPrecloseReport] = useState<PrecloseReport | null>(null);
  const [reportExplanation, setReportExplanation] = useState<ReportExplanation | null>(null);

  const [tradeForm, setTradeForm] = useState<TradeForm>(emptyTradeForm);
  const [formError, setFormError] = useState("");
  const [submitState, setSubmitState] = useState("等待录入");
  const [explainState, setExplainState] = useState("等待生成");
  const [watchlistState, setWatchlistState] = useState("等待编辑");
  const [watchlistError, setWatchlistError] = useState("");

  const stateDistribution = precloseReport?.state_distribution ?? {};
  const healthLabel = health?.status === "ok" ? "正常跟踪" : "数据不足";
  const hasBackendError = Object.keys(errors).length > 0;

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setLoadState("loading");
    const [
      healthResult,
      configResult,
      watchlistResult,
      indicatorResult,
      tradeResult,
      pnlResult,
      riskResult,
      waveResult,
      reportResult,
    ] = await Promise.all([
      apiGet<HealthResponse>("/api/health"),
      apiGet<ConfigStatus>("/api/config/status"),
      apiGet<WatchlistResponse>("/api/watchlist"),
      apiGet<IndicatorResponse>("/api/indicators/snapshot"),
      apiGet<TradeResponse>("/api/ledger/trades"),
      apiGet<PnlResponse>("/api/ledger/summary"),
      apiGet<RiskSummary>("/api/risk/summary"),
      apiGet<WaveStatesResponse>("/api/wave/states"),
      apiGet<PrecloseReport>("/api/reports/preclose"),
    ]);

    applyResult("health", healthResult, setHealth);
    applyResult("config", configResult, setConfig);
    if (watchlistResult.ok) {
      setWatchlist(watchlistResult.data);
      setWatchlistError("");
      clearError("watchlist");
    } else {
      setWatchlist({ version: 1, items: [] });
      setError("watchlist", watchlistResult.error);
    }
    if (indicatorResult.ok) {
      setIndicators(indicatorResult.data.items);
      setIndicatorProvider(indicatorResult.data.provider);
      clearError("indicators");
    } else {
      setIndicators([]);
      setError("indicators", indicatorResult.error);
    }
    if (tradeResult.ok) {
      setTrades(tradeResult.data.items);
      clearError("trades");
    } else {
      setTrades([]);
      setError("trades", tradeResult.error);
    }
    if (pnlResult.ok) {
      setPnlItems(pnlResult.data.items);
      clearError("pnl");
    } else {
      setPnlItems([]);
      setError("pnl", pnlResult.error);
    }
    applyResult("risk", riskResult, setRiskSummary);
    if (waveResult.ok) {
      setWaveStates(waveResult.data.items);
      clearError("wave");
    } else {
      setWaveStates([]);
      setError("wave", waveResult.error);
    }
    applyResult("report", reportResult, setPrecloseReport);
    setLoadState(hasAnyError([healthResult, configResult, watchlistResult, indicatorResult, tradeResult, pnlResult, riskResult, waveResult, reportResult]) ? "error" : "ready");
  }

  async function refreshPortfolio() {
    const [tradeResult, pnlResult, riskResult, waveResult, reportResult] = await Promise.all([
      apiGet<TradeResponse>("/api/ledger/trades"),
      apiGet<PnlResponse>("/api/ledger/summary"),
      apiGet<RiskSummary>("/api/risk/summary"),
      apiGet<WaveStatesResponse>("/api/wave/states"),
      apiGet<PrecloseReport>("/api/reports/preclose"),
    ]);
    if (tradeResult.ok) {
      setTrades(tradeResult.data.items);
      clearError("trades");
    } else {
      setError("trades", tradeResult.error);
    }
    if (pnlResult.ok) {
      setPnlItems(pnlResult.data.items);
      clearError("pnl");
    } else {
      setError("pnl", pnlResult.error);
    }
    applyResult("risk", riskResult, setRiskSummary);
    if (waveResult.ok) {
      setWaveStates(waveResult.data.items);
      clearError("wave");
    } else {
      setError("wave", waveResult.error);
    }
    applyResult("report", reportResult, setPrecloseReport);
  }

  function applyResult<T>(
    key: string,
    result: ApiResult<T>,
    setter: (value: T) => void,
  ) {
    if (result.ok) {
      setter(result.data);
      clearError(key);
    } else {
      setError(key, result.error);
    }
  }

  function setError(key: string, value: string) {
    setErrors((current) => ({ ...current, [key]: value }));
  }

  function clearError(key: string) {
    setErrors((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function updateTradeForm(
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) {
    const { name, value } = event.target;
    setTradeForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function submitTrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateTradeForm(tradeForm);
    if (validationError) {
      setFormError(validationError);
      return;
    }
    setFormError("");
    setSubmitState("保存中");
    const result = await apiPost<TradeForm, TradeRecord>("/api/ledger/trades", tradeForm);
    if (!result.ok) {
      setSubmitState("保存失败");
      setFormError("后端暂不可用或输入未通过校验");
      return;
    }
    setSubmitState("已保存");
    setTradeForm({
      ...emptyTradeForm,
      trade_date: tradeForm.trade_date,
      instrument_name: tradeForm.instrument_name,
      instrument_code: tradeForm.instrument_code,
      side: tradeForm.side,
    });
    await refreshPortfolio();
  }

  function updateWatchlistItem(
    index: number,
    field: keyof WatchlistItem,
    value: string | boolean,
  ) {
    setWatchlist((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  function addWatchlistItem() {
    setWatchlist((current) => ({
      ...current,
      items: [...current.items, { ...emptyWatchlistItem }],
    }));
    setWatchlistState("编辑中");
  }

  function removeWatchlistItem(index: number) {
    setWatchlist((current) => ({
      ...current,
      items: current.items.filter((_, itemIndex) => itemIndex !== index),
    }));
    setWatchlistState("编辑中");
  }

  async function validateWatchlist() {
    const localError = validateWatchlistDraft(watchlist);
    if (localError) {
      setWatchlistError(localError);
      setWatchlistState("校验失败");
      return;
    }
    const result = await apiPost<WatchlistResponse, WatchlistValidation>(
      "/api/watchlist/validate",
      watchlist,
    );
    if (!result.ok) {
      setWatchlistError("后端暂不可用，无法校验配置");
      setWatchlistState("校验失败");
      return;
    }
    setWatchlistError(result.data.errors.join(" / "));
    setWatchlistState(result.data.valid ? "校验通过" : "校验失败");
  }

  async function saveWatchlist() {
    const localError = validateWatchlistDraft(watchlist);
    if (localError) {
      setWatchlistError(localError);
      setWatchlistState("保存失败");
      return;
    }
    setWatchlistState("保存中");
    const result = await apiPut<WatchlistResponse, WatchlistResponse>(
      "/api/watchlist",
      watchlist,
    );
    if (!result.ok) {
      setWatchlistError("配置保存失败，请检查名称、代码和市场格式");
      setWatchlistState("保存失败");
      return;
    }
    setWatchlist(result.data);
    setWatchlistError("");
    setWatchlistState("已保存");
    await loadAll();
  }

  async function explainReport() {
    setExplainState("生成中");
    const result = await apiPost<
      { report?: PrecloseReport; as_of?: string },
      ReportExplanation
    >(
      "/api/reports/preclose/explain",
      precloseReport
        ? { report: precloseReport }
        : { as_of: new Date().toISOString().slice(0, 19) },
    );
    if (!result.ok) {
      setExplainState("Codex 不可用");
      return;
    }
    setReportExplanation(result.data);
    setExplainState(result.data.success ? "已生成" : "生成失败");
  }

  function renderActiveTab() {
    if (activeTab === "overview") {
      return (
        <OverviewView
          healthLabel={healthLabel}
          loadState={loadState}
          provider={indicatorProvider}
          config={config}
          riskSummary={riskSummary}
          stateDistribution={stateDistribution}
          riskFlags={precloseReport?.risk_flags ?? []}
          hasBackendError={hasBackendError}
        />
      );
    }
    if (activeTab === "indicators") {
      return <IndicatorsView rows={indicators} error={errors.indicators} />;
    }
    if (activeTab === "risk") {
      return <RiskView riskSummary={riskSummary} error={errors.risk} />;
    }
    if (activeTab === "wave") {
      return <WaveView rows={waveStates} error={errors.wave} />;
    }
    if (activeTab === "ledger") {
      return (
        <LedgerView
          form={tradeForm}
          formError={formError}
          submitState={submitState}
          trades={trades}
          pnlItems={pnlItems}
          onChange={updateTradeForm}
          onSubmit={submitTrade}
          error={errors.trades ?? errors.pnl}
        />
      );
    }
    if (activeTab === "report") {
      return (
        <ReportView
          report={precloseReport}
          explanation={reportExplanation}
          explainState={explainState}
          onExplain={explainReport}
          error={errors.report}
        />
      );
    }
    return (
      <SettingsWithWatchlist
        config={config}
        error={errors.config}
        watchlist={watchlist}
        watchlistError={watchlistError || errors.watchlist}
        watchlistState={watchlistState}
        onAddWatchlistItem={addWatchlistItem}
        onRemoveWatchlistItem={removeWatchlistItem}
        onSaveWatchlist={() => void saveWatchlist()}
        onValidateWatchlist={() => void validateWatchlist()}
        onWatchlistItemChange={updateWatchlistItem}
      />
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">波段观察</div>
        <nav aria-label="主导航">
          {tabs.map((tab) => (
            <button
              className={activeTab === tab.id ? "active" : ""}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>
      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">本地 Web MVP / Mock 模式</p>
            <h1>A 股自选股波段切换决策助手</h1>
          </div>
          <div className="topbar-actions">
            <button type="button" onClick={() => void loadAll()}>
              刷新
            </button>
            <span className="status-pill">{statusText(loadState)}</span>
          </div>
        </header>

        {hasBackendError ? (
          <div className="notice">
            后端部分接口暂不可用；页面保留已加载数据，并在对应区域显示状态。
          </div>
        ) : null}

        {renderActiveTab()}

        <p className="risk-notice">
          本工具仅展示基于本地规则和当前数据的观察结果，不构成投资建议。请结合个人风险承受能力独立决策。
        </p>
      </section>
    </main>
  );
}

function OverviewView(props: {
  healthLabel: string;
  loadState: LoadState;
  provider: string;
  config: ConfigStatus | null;
  riskSummary: RiskSummary;
  stateDistribution: Record<string, number>;
  riskFlags: string[];
  hasBackendError: boolean;
}) {
  return (
    <section className="view-stack">
      <section className="metric-strip" aria-label="总览">
        <Metric label="健康状态" value={props.healthLabel} />
        <Metric label="数据源" value={props.provider} />
        <Metric label="Codex" value={props.config?.codex.enabled ? "已启用" : "fake"} />
        <Metric label="连接状态" value={statusText(props.loadState)} />
      </section>
      <section className="metric-strip" aria-label="组合关键指标">
        <Metric label="总持仓市值" value={moneyText(props.riskSummary.total_market_value)} />
        <Metric label="总盈亏" value={moneyText(props.riskSummary.total_pnl)} />
        <Metric
          label="最大单标的占比"
          value={percentText(props.riskSummary.max_single_position.position_weight_pct)}
        />
        <Metric label="数据状态" value={statusLabel(props.riskSummary.data_status)} />
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>状态分布与风险标记</h2>
          <p>{props.hasBackendError ? "部分接口不可用" : "已加载"}</p>
        </div>
        <div className="overview-grid">
          <TextBlock title="状态分布" value={stateDistributionText(props.stateDistribution)} />
          <TextBlock title="风险标记" value={listText(props.riskFlags)} />
          <TextBlock
            title="Codex 自检"
            value={`enabled=${String(props.config?.codex.enabled ?? false)} / model=${props.config?.codex.model ?? "-"} / version=${props.config?.codex.version_check ?? "-"}`}
          />
        </div>
      </section>
    </section>
  );
}

function IndicatorsView(props: { rows: IndicatorRow[]; error?: string }) {
  return (
    <section className="panel">
      <PanelHeading title="自选股指标" status={props.error ? "后端不可用" : `${props.rows.length} 条`} />
      {props.error ? <EmptyState text="指标接口暂不可用" /> : null}
      <DataTable
        emptyText="暂无指标"
        headers={["名称", "最新日期", "收盘价", "MA20", "MA60", "5 日动量", "10 日动量", "20 日动量", "数据状态"]}
        rows={props.rows.map((row) => [
          row.name,
          row.latest_trade_date ?? "-",
          formatNumber(row.latest_close),
          formatNumber(row.indicators.ma20),
          formatNumber(row.indicators.ma60),
          formatPercent(row.indicators.momentum_5d_pct),
          formatPercent(row.indicators.momentum_10d_pct),
          formatPercent(row.indicators.momentum_20d_pct),
          statusLabel(row.data_status),
        ])}
      />
    </section>
  );
}

function RiskView(props: { riskSummary: RiskSummary; error?: string }) {
  return (
    <section className="view-stack">
      <section className="metric-strip" aria-label="组合风控">
        <Metric label="总持仓市值" value={moneyText(props.riskSummary.total_market_value)} />
        <Metric label="浮动盈亏" value={moneyText(props.riskSummary.floating_pnl)} />
        <Metric label="已实现盈亏" value={moneyText(props.riskSummary.realized_pnl)} />
        <Metric label="数据状态" value={statusLabel(props.riskSummary.data_status)} />
      </section>
      <section className="panel">
        <PanelHeading title="方向 / 分组集中度" status={props.error ? "后端不可用" : "当前持仓"} />
        <div className="two-column">
          <DataTable
            emptyText="暂无方向集中度"
            headers={["方向", "市值", "占比", "状态"]}
            rows={props.riskSummary.direction_concentration.map((item) => [
              item.name,
              moneyText(item.market_value),
              percentText(item.weight_pct),
              riskStatusLabel(item.risk_status),
            ])}
          />
          <DataTable
            emptyText="暂无分组集中度"
            headers={["分组", "市值", "占比", "状态"]}
            rows={props.riskSummary.group_concentration.map((item) => [
              item.name,
              moneyText(item.market_value),
              percentText(item.weight_pct),
              riskStatusLabel(item.risk_status),
            ])}
          />
        </div>
      </section>
    </section>
  );
}

function WaveView(props: { rows: WaveStateItem[]; error?: string }) {
  return (
    <section className="panel">
      <PanelHeading title="波段状态" status={props.error ? "后端不可用" : `${props.rows.length} 条`} />
      <DataTable
        emptyText="暂无波段状态"
        headers={["名称", "状态", "总分", "主要原因", "MA20", "MA60", "动量", "数据状态"]}
        rows={props.rows.map((item) => [
          item.name,
          item.wave_state.label_cn,
          scoreText(item.wave_state.total_score),
          reasonText(item.wave_state.reasons),
          formatNumber(item.indicator_summary.ma20),
          formatNumber(item.indicator_summary.ma60),
          formatPercent(item.indicator_summary.momentum_20d_pct),
          statusLabel(item.data_status),
        ])}
      />
    </section>
  );
}

function LedgerView(props: {
  form: TradeForm;
  formError: string;
  submitState: string;
  trades: TradeRecord[];
  pnlItems: PnlItem[];
  onChange: (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  error?: string;
}) {
  return (
    <section className="view-stack">
      <section className="ledger-grid">
        <section className="panel">
          <PanelHeading title="手动成交记录" status={props.submitState} />
          <form className="trade-form" onSubmit={props.onSubmit}>
            <FormField label="名称" name="instrument_name" required value={props.form.instrument_name} onChange={props.onChange} />
            <FormField label="代码" name="instrument_code" value={props.form.instrument_code} onChange={props.onChange} />
            <FormField label="日期" name="trade_date" required type="date" value={props.form.trade_date} onChange={props.onChange} />
            <label>
              <span>方向</span>
              <select name="side" value={props.form.side} onChange={props.onChange}>
                <option value="increase_position">增加持仓</option>
                <option value="decrease_position">减少持仓</option>
              </select>
            </label>
            <FormField label="数量" name="quantity" required value={props.form.quantity} onChange={props.onChange} />
            <FormField label="价格" name="price" required value={props.form.price} onChange={props.onChange} />
            <FormField label="费用" name="fee" value={props.form.fee} onChange={props.onChange} />
            <label className="form-wide">
              <span>备注</span>
              <textarea name="note" rows={2} value={props.form.note} onChange={props.onChange} />
            </label>
            <div className="form-actions">
              <button type="submit">保存记录</button>
              <span>{props.formError || props.error || props.submitState}</span>
            </div>
          </form>
        </section>
        <section className="panel">
          <PanelHeading title="成交记录" status={`${props.trades.length} 条`} />
          <DataTable
            emptyText="暂无记录"
            headers={["名称", "日期", "方向", "数量", "价格", "费用", "备注"]}
            rows={props.trades.map((trade) => [
              trade.instrument_name,
              trade.trade_date,
              sideLabel(trade.side),
              trade.quantity,
              trade.price,
              trade.fee,
              trade.note || "-",
            ])}
          />
        </section>
      </section>
      <section className="panel">
        <PanelHeading title="盈亏摘要" status="移动平均成本法" />
        <DataTable
          emptyText="暂无摘要"
          headers={["名称", "持仓数量", "平均成本", "当前市值", "未实现盈亏", "总盈亏", "状态"]}
          rows={props.pnlItems.map((item) => [
            item.instrument_name,
            item.quantity,
            moneyText(item.average_cost),
            moneyText(item.current_market_value),
            moneyText(item.unrealized_pnl),
            moneyText(item.total_pnl),
            statusLabel(item.status),
          ])}
        />
      </section>
    </section>
  );
}

function ReportView(props: {
  report: PrecloseReport | null;
  explanation: ReportExplanation | null;
  explainState: string;
  onExplain: () => void;
  error?: string;
}) {
  return (
    <section className="view-stack">
      <section className="panel">
        <PanelHeading title="14:55 结构化报告" status={props.error ? "后端不可用" : props.report?.report_status ?? "暂无"} />
        <section className="metric-strip inner-strip" aria-label="14:55 报告摘要">
          <Metric label="市场时段状态" value={sessionStatusLabel(props.report?.market_session_status.status)} />
          <Metric label="报告状态" value={reportStatusLabel(props.report?.report_status)} />
          <Metric label="数据状态" value={statusLabel(props.report?.data_status ?? "")} />
          <Metric label="生成时间" value={props.report ? `${props.report.as_of_date} ${props.report.as_of_time}` : "-"} />
        </section>
        <section className="report-lists">
          <TextBlock title="风险标记" value={listText(props.report?.risk_flags)} />
          <TextBlock title="状态分布" value={stateDistributionText(props.report?.state_distribution)} />
          <TextBlock title="重点观察项" value={itemListText(props.report?.attention_items)} />
          <TextBlock title="仓位复核候选" value={itemListText(props.report?.position_review_candidates)} />
          <TextBlock title="切换观察候选" value={itemListText(props.report?.rotation_watch_candidates)} />
          <TextBlock title="数据质量提示" value={listText(props.report?.data_quality_notes)} />
        </section>
      </section>
      <section className="panel">
        <PanelHeading title="解释摘要" status={props.explainState} />
        <div className="report-explanation">
          <div className="form-actions">
            <button type="button" onClick={props.onExplain}>
              生成解释摘要
            </button>
            <span>{props.explanation ? `provider: ${props.explanation.provider}` : props.explainState}</span>
          </div>
          <pre>{props.explanation?.text || "暂无解释摘要"}</pre>
        </div>
      </section>
    </section>
  );
}

function SettingsWithWatchlist(props: {
  config: ConfigStatus | null;
  error?: string;
  watchlist: WatchlistResponse;
  watchlistError?: string;
  watchlistState: string;
  onAddWatchlistItem: () => void;
  onRemoveWatchlistItem: (index: number) => void;
  onSaveWatchlist: () => void;
  onValidateWatchlist: () => void;
  onWatchlistItemChange: (
    index: number,
    field: keyof WatchlistItem,
    value: string | boolean,
  ) => void;
}) {
  return (
    <section className="view-stack">
      <SettingsView config={props.config} error={props.error} />
      <WatchlistEditor
        error={props.watchlistError}
        state={props.watchlistState}
        value={props.watchlist}
        onAdd={props.onAddWatchlistItem}
        onChange={props.onWatchlistItemChange}
        onRemove={props.onRemoveWatchlistItem}
        onSave={props.onSaveWatchlist}
        onValidate={props.onValidateWatchlist}
      />
    </section>
  );
}

function WatchlistEditor(props: {
  value: WatchlistResponse;
  state: string;
  error?: string;
  onAdd: () => void;
  onChange: (index: number, field: keyof WatchlistItem, value: string | boolean) => void;
  onRemove: (index: number) => void;
  onSave: () => void;
  onValidate: () => void;
}) {
  return (
    <section className="panel">
      <PanelHeading title="自选股配置" status={props.state} />
      {props.error ? <div className="notice watchlist-notice">{props.error}</div> : null}
      <div className="watchlist-editor">
        {props.value.items.length === 0 ? <EmptyState text="暂无配置项" /> : null}
        {props.value.items.map((item, index) => (
          <article className="watchlist-row" key={`${item.name}-${index}`}>
            <label className="inline-check">
              <input
                checked={item.enabled}
                type="checkbox"
                onChange={(event) =>
                  props.onChange(index, "enabled", event.target.checked)
                }
              />
              <span>{item.enabled ? "启用" : "停用"}</span>
            </label>
            <div className="watchlist-grid">
              <WatchlistField
                label="名称"
                value={item.name}
                onChange={(value) => props.onChange(index, "name", value)}
              />
              <WatchlistField
                label="代码"
                value={item.symbol}
                onChange={(value) => props.onChange(index, "symbol", value.toUpperCase())}
              />
              <WatchlistField
                label="市场"
                value={item.market}
                onChange={(value) => props.onChange(index, "market", value.toUpperCase())}
              />
              <WatchlistField
                label="分组"
                value={item.group}
                onChange={(value) => props.onChange(index, "group", value)}
              />
              <WatchlistField
                label="主题"
                value={item.theme}
                onChange={(value) => props.onChange(index, "theme", value)}
              />
              <label>
                <span>观察理由</span>
                <textarea
                  rows={2}
                  value={item.observation_note}
                  onChange={(event) =>
                    props.onChange(index, "observation_note", event.target.value)
                  }
                />
              </label>
              <label>
                <span>风险点</span>
                <textarea
                  rows={2}
                  value={item.risk_note}
                  onChange={(event) =>
                    props.onChange(index, "risk_note", event.target.value)
                  }
                />
              </label>
            </div>
            <div className="row-actions">
              <button type="button" className="secondary-button" onClick={() => props.onRemove(index)}>
                删除
              </button>
            </div>
          </article>
        ))}
      </div>
      <div className="form-actions watchlist-actions">
        <button type="button" onClick={props.onAdd}>
          新增标的
        </button>
        <button type="button" className="secondary-button" onClick={props.onValidate}>
          校验格式
        </button>
        <button type="button" onClick={props.onSave}>
          保存配置
        </button>
        <span>{props.error || props.state}</span>
      </div>
    </section>
  );
}

function WatchlistField(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <span>{props.label}</span>
      <input value={props.value} onChange={(event) => props.onChange(event.target.value)} />
    </label>
  );
}

function SettingsView(props: { config: ConfigStatus | null; error?: string }) {
  return (
    <section className="panel">
      <PanelHeading title="设置 / 自检" status={props.error ? "后端不可用" : "安全摘要"} />
      <section className="settings-grid">
        <TextBlock title="应用模式" value={props.config?.mode ?? "-"} />
        <TextBlock title="行情 provider" value={props.config?.providers.market ?? "-"} />
        <TextBlock title="LLM provider" value={props.config?.providers.llm ?? "-"} />
        <TextBlock title="Codex enabled" value={String(props.config?.codex.enabled ?? false)} />
        <TextBlock title="Codex 模型" value={props.config?.codex.model ?? "-"} />
        <TextBlock title="version_check" value={props.config?.codex.version_check ?? "-"} />
        <TextBlock title="sandbox" value={props.config?.codex.sandbox_mode ?? "-"} />
        <TextBlock title="数据库" value={props.config?.database.configured ? "已配置" : "未配置"} />
      </section>
    </section>
  );
}

function Metric(props: { label: string; value: string }) {
  return (
    <article className="metric">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </article>
  );
}

function PanelHeading(props: { title: string; status: string }) {
  return (
    <div className="panel-heading">
      <h2>{props.title}</h2>
      <p>{props.status}</p>
    </div>
  );
}

function DataTable(props: { headers: string[]; rows: string[][]; emptyText: string }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {props.headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.length === 0 ? (
            <tr>
              <td colSpan={props.headers.length}>{props.emptyText}</td>
            </tr>
          ) : (
            props.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function TextBlock(props: { title: string; value: string }) {
  return (
    <article className="text-block">
      <h3>{props.title}</h3>
      <p>{props.value}</p>
    </article>
  );
}

function EmptyState(props: { text: string }) {
  return <div className="empty-state">{props.text}</div>;
}

function FormField(props: {
  label: string;
  name: keyof TradeForm;
  value: string;
  required?: boolean;
  type?: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label>
      <span>{props.label}</span>
      <input
        name={props.name}
        required={props.required}
        type={props.type ?? "text"}
        value={props.value}
        onChange={props.onChange}
      />
    </label>
  );
}

function validateTradeForm(form: TradeForm): string {
  if (!form.instrument_name.trim()) {
    return "名称不能为空";
  }
  if (!form.trade_date.trim()) {
    return "日期不能为空";
  }
  if (Number(form.quantity) <= 0 || Number.isNaN(Number(form.quantity))) {
    return "数量必须大于 0";
  }
  if (Number(form.price) < 0 || Number.isNaN(Number(form.price))) {
    return "价格不能为负";
  }
  if (Number(form.fee) < 0 || Number.isNaN(Number(form.fee))) {
    return "费用不能为负";
  }
  return "";
}

function validateWatchlistDraft(value: WatchlistResponse): string {
  const symbolPattern = /^\d{6}\.(SH|SZ|BJ)$/;
  const validMarkets = new Set(["", "SH", "SZ", "BJ"]);
  if (value.items.length === 0) {
    return "至少保留 1 个自选股条目";
  }
  const names = new Set<string>();
  const symbols = new Set<string>();
  for (let index = 0; index < value.items.length; index += 1) {
    const item = value.items[index];
    const name = item.name.trim();
    if (!name) {
      return `第 ${index + 1} 行名称不能为空`;
    }
    if (names.has(name)) {
      return `名称重复：${name}`;
    }
    names.add(name);
    const symbol = item.symbol.trim().toUpperCase();
    if (symbol && !symbolPattern.test(symbol)) {
      return `第 ${index + 1} 行代码格式应类似 600000.SH`;
    }
    if (symbol && symbols.has(symbol)) {
      return `代码重复：${symbol}`;
    }
    if (symbol) {
      symbols.add(symbol);
    }
    const market = item.market.trim().toUpperCase();
    if (!validMarkets.has(market)) {
      return `第 ${index + 1} 行市场仅支持 SH/SZ/BJ 或留空`;
    }
  }
  return "";
}

function hasAnyError(results: Array<ApiResult<unknown>>): boolean {
  return results.some((result) => !result.ok);
}

function statusText(state: LoadState): string {
  if (state === "ready") {
    return "API 已连接";
  }
  if (state === "loading") {
    return "加载中";
  }
  if (state === "error") {
    return "部分可用";
  }
  return "等待连接";
}

function formatNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return value.toFixed(2);
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return `${value.toFixed(2)}%`;
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

function sideLabel(side: TradeSide): string {
  return side === "increase_position" ? "增加持仓" : "减少持仓";
}

function moneyText(value: string | null): string {
  if (value === null || value === "") {
    return "-";
  }
  return Number(value).toFixed(2);
}

function percentText(value: string | null): string {
  if (value === null || value === "") {
    return "-";
  }
  return `${Number(value).toFixed(2)}%`;
}

function scoreText(value: string): string {
  return Number(value).toFixed(2);
}

function statusLabel(status: string): string {
  if (status === "ok" || status === "ready") {
    return "正常跟踪";
  }
  if (status === "price_missing" || status === "data_insufficient" || status === "non_trading_day") {
    return "数据不足";
  }
  return "需要复盘";
}

function riskStatusLabel(status: string): string {
  if (status === "normal") {
    return "正常跟踪";
  }
  if (status === "high_concentration") {
    return "仓位复核候选";
  }
  if (status === "data_insufficient") {
    return "数据不足";
  }
  return "需要复盘";
}

function reasonText(reasons: string[]): string {
  if (reasons.length === 0) {
    return "-";
  }
  return reasons.slice(0, 2).join(" / ");
}

function sessionStatusLabel(status: string | undefined): string {
  if (!status) {
    return "-";
  }
  const labels: Record<string, string> = {
    preclose: "14:55",
    morning_session: "上午交易时段",
    afternoon_session: "下午交易时段",
    lunch_break: "午间休市",
    before_open: "开盘前",
    after_close: "收盘后",
    non_trading_day: "非交易日",
  };
  return labels[status] ?? status;
}

function reportStatusLabel(status: string | undefined): string {
  if (status === "ready") {
    return "正常跟踪";
  }
  if (status === "partial") {
    return "需要复盘";
  }
  if (status === "blocked") {
    return "数据不足";
  }
  return "-";
}

function itemListText(items: ReportListItem[] | undefined): string {
  if (!items || items.length === 0) {
    return "-";
  }
  return items
    .slice(0, 4)
    .map((item) => `${item.name} ${scoreText(item.total_score)}`)
    .join(" / ");
}

function listText(items: string[] | undefined): string {
  if (!items || items.length === 0) {
    return "-";
  }
  return items.slice(0, 4).join(" / ");
}

function stateDistributionText(distribution: Record<string, number> | undefined): string {
  if (!distribution || Object.keys(distribution).length === 0) {
    return "-";
  }
  return Object.entries(distribution)
    .map(([state, count]) => `${waveStateLabel(state)} ${count}`)
    .join(" / ");
}

function waveStateLabel(state: string): string {
  const labels: Record<string, string> = {
    focus_watch: "重点观察",
    normal_tracking: "正常跟踪",
    risk_attention: "风险关注",
    data_insufficient: "数据不足",
    position_review_candidate: "仓位复核候选",
    rotation_watch_candidate: "切换观察候选",
    needs_review: "需要复盘",
  };
  return labels[state] ?? state;
}
