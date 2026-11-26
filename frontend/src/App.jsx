import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

const tabs = [
  { id: "twin", label: "Nutrition Twin" },
  { id: "explorer", label: "Nutrition Explorer" },
  { id: "discover", label: "Intent Search" },
  { id: "repair", label: "Meal Repair" },
  { id: "recommend", label: "Why This Food?" },
  { id: "planner", label: "Smart Planner" },
  { id: "indian", label: "Indian Lens" },
];

const goalOptions = [
  { value: "balanced_diet", label: "Balanced Diet" },
  { value: "weight_loss", label: "Weight Loss" },
  { value: "muscle_gain", label: "Muscle Gain" },
  { value: "diabetic_friendly", label: "Diabetic Friendly" },
  { value: "heart_health", label: "Heart Health" },
];

const restrictionOptions = ["vegetarian", "vegan", "jain", "gluten_free", "dairy_free"];
const allergyOptions = ["nuts", "dairy", "eggs", "soy", "wheat", "fish"];

function SettingsPanel({ settings, llmConfig, onConfigChange, onLoadProfile }) {
  return (
    <aside className="panel settings-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Control Room</p>
          <h2>Workspace Settings</h2>
        </div>
        <button className="secondary-button" onClick={onLoadProfile} type="button">
          Load User
        </button>
      </div>

      <label>
        <span>User ID</span>
        <input
          value={llmConfig.user_id}
          onChange={(event) => onConfigChange("user_id", event.target.value)}
          placeholder="guest_123"
        />
      </label>
      <label className="toggle-row">
        <span>Use LM Studio</span>
        <input
          type="checkbox"
          checked={llmConfig.use_lmstudio}
          onChange={(event) => onConfigChange("use_lmstudio", event.target.checked)}
        />
      </label>
      <label>
        <span>LM Studio URL</span>
        <input
          value={llmConfig.lmstudio_url}
          onChange={(event) => onConfigChange("lmstudio_url", event.target.value)}
        />
      </label>
      <label>
        <span>LM Studio Model</span>
        <input
          value={llmConfig.lmstudio_model}
          onChange={(event) => onConfigChange("lmstudio_model", event.target.value)}
        />
      </label>
      <p className="settings-note">
        Dataset: <strong>{settings?.dataset_path || "Loading..."}</strong>
      </p>
      <p className="settings-note">
        NutriWise now runs as a profile-driven nutrition coach with explainable recommendations and Indian meal intelligence.
      </p>
    </aside>
  );
}

function MetricGrid({ items }) {
  return (
    <div className="metric-grid">
      {items.map((item) => (
        <article className="metric-card" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </div>
  );
}

function TagList({ items }) {
  if (!items?.length) return <p className="muted-copy">No selections yet.</p>;
  return (
    <div className="tag-list">
      {items.map((item) => (
        <span className="tag" key={item}>
          {item.replaceAll("_", " ")}
        </span>
      ))}
    </div>
  );
}

function FoodCard({ item }) {
  return (
    <article className="food-card">
      <div className="food-card-header">
        <div>
          <h3>{item.food_name}</h3>
          <p>{item.category} • {item.serving_unit}</p>
        </div>
        <span className="score-chip">Score {item.score}</span>
      </div>
      <MetricGrid
        items={[
          { label: "Calories", value: item.calories },
          { label: "Protein", value: `${item.protein_g} g` },
          { label: "Carbs", value: `${item.carbs_g} g` },
          { label: "Fat", value: `${item.fat_g} g` },
          { label: "Fiber", value: `${item.fiber_g} g` },
        ]}
      />
      <TagList items={item.cuisine_tags} />
      <ul className="flat-list">
        {(item.why_this_food || []).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      {item.healthier_swap ? <p className="muted-copy">Smarter swap: {item.healthier_swap}</p> : null}
    </article>
  );
}

function SectionShell({ title, subtitle, children, actions }) {
  return (
    <section className="panel section-shell">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

function App() {
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState("twin");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [llmConfig, setLlmConfig] = useState({
    user_id: "guest_123",
    use_lmstudio: true,
    lmstudio_url: "http://localhost:1234/v1/chat/completions",
    lmstudio_model: "openchat-3.6-8b-20240522",
  });
  const [profileForm, setProfileForm] = useState({
    user_id: "guest_123",
    age: 25,
    weight: 70,
    height: 170,
    gender: "female",
    activity_level: "moderate",
    health_goals: ["balanced_diet"],
    dietary_restrictions: ["vegetarian"],
    allergies: [],
    health_conditions: [],
    cuisine_preferences: ["indian"],
    budget_preference: "medium",
    max_prep_time: 30,
  });
  const [profileResult, setProfileResult] = useState(null);
  const [discoverQuery, setDiscoverQuery] = useState("high protein vegetarian breakfast under 300 calories");
  const [discoverResult, setDiscoverResult] = useState(null);
  const [lookupQuery, setLookupQuery] = useState("paneer");
  const [lookupResult, setLookupResult] = useState(null);
  const [compareForm, setCompareForm] = useState({ first: "paneer", second: "tofu" });
  const [compareResult, setCompareResult] = useState(null);
  const [repairQuery, setRepairQuery] = useState("poha and chai with biscuits");
  const [repairResult, setRepairResult] = useState(null);
  const [recommendForm, setRecommendForm] = useState({ meal_type: "lunch", query: "iron rich vegetarian lunch" });
  const [recommendResult, setRecommendResult] = useState(null);
  const [plannerForm, setPlannerForm] = useState({
    query: "budget friendly Indian meals",
    pantry_items: "paneer, oats, rice, tomato, spinach",
    budget_preference: "medium",
    max_prep_time: 25,
  });
  const [plannerResult, setPlannerResult] = useState(null);
  const [indianQuery, setIndianQuery] = useState("samosa and chai");
  const [indianResult, setIndianResult] = useState(null);
  const [historyResult, setHistoryResult] = useState([]);

  useEffect(() => {
    async function bootstrap() {
      try {
        const response = await fetch(`${API_BASE_URL}/settings`);
        if (!response.ok) {
          throw new Error(`Settings request failed with status ${response.status}`);
        }
        const data = await response.json();
        setSettings(data);
        setLlmConfig((current) => ({
          ...current,
          use_lmstudio: data.default_use_lmstudio,
          lmstudio_url: data.lmstudio_url,
          lmstudio_model: data.lmstudio_model,
        }));
      } catch (requestError) {
        setError(requestError.message || "Unable to load backend settings.");
      }
    }

    bootstrap();
  }, []);

  useEffect(() => {
    setProfileForm((current) => ({ ...current, user_id: llmConfig.user_id }));
  }, [llmConfig.user_id]);

  async function apiRequest(endpoint, payload, method = "POST") {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: method === "GET" ? undefined : JSON.stringify(payload),
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const errorBody = await response.json();
        message = errorBody.detail || errorBody.error || message;
      } catch {
        // no-op
      }
      throw new Error(message);
    }

    return response.json();
  }

  async function withLoading(callback) {
    setLoading(true);
    setError("");
    try {
      await callback();
    } catch (requestError) {
      setError(requestError.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function updateProfileField(field, value) {
    setProfileForm((current) => ({ ...current, [field]: value }));
  }

  function toggleSelection(field, value) {
    setProfileForm((current) => {
      const currentValues = current[field];
      const exists = currentValues.includes(value);
      return {
        ...current,
        [field]: exists ? currentValues.filter((item) => item !== value) : [...currentValues, value],
      };
    });
  }

  async function saveProfile() {
    await withLoading(async () => {
      const data = await apiRequest("/profile", profileForm);
      setProfileResult(data);
      const history = await apiRequest(`/history/${profileForm.user_id}`, {}, "GET");
      setHistoryResult(history.history || []);
    });
  }

  async function loadProfile() {
    await withLoading(async () => {
      const profile = await apiRequest(`/profile/${llmConfig.user_id}`, {}, "GET");
      setProfileResult(profile);
      setProfileForm(profile);
      const history = await apiRequest(`/history/${llmConfig.user_id}`, {}, "GET");
      setHistoryResult(history.history || []);
    });
  }

  async function runDiscover() {
    await withLoading(async () => {
      const data = await apiRequest("/discover", {
        user_id: profileForm.user_id,
        query: discoverQuery,
        top_k: 8,
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setDiscoverResult(data);
    });
  }

  async function runLookup() {
    await withLoading(async () => {
      const data = await apiRequest("/food-lookup", {
        user_id: profileForm.user_id,
        query: lookupQuery,
        top_k: 5,
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setLookupResult(data);
    });
  }

  async function runCompare() {
    await withLoading(async () => {
      const data = await apiRequest("/food-compare", {
        user_id: profileForm.user_id,
        first_query: compareForm.first,
        second_query: compareForm.second,
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setCompareResult(data);
    });
  }

  async function runRepair() {
    await withLoading(async () => {
      const data = await apiRequest("/meal-repair", {
        user_id: profileForm.user_id,
        meal_text: repairQuery,
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setRepairResult(data);
    });
  }

  async function runRecommendations() {
    await withLoading(async () => {
      const data = await apiRequest("/recommendations/personalized", {
        user_id: profileForm.user_id,
        meal_type: recommendForm.meal_type,
        query: recommendForm.query,
        top_k: 6,
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setRecommendResult(data);
      const history = await apiRequest(`/history/${profileForm.user_id}`, {}, "GET");
      setHistoryResult(history.history || []);
    });
  }

  async function runPlanner() {
    await withLoading(async () => {
      const data = await apiRequest("/smart-plan", {
        user_id: profileForm.user_id,
        query: plannerForm.query,
        pantry_items: plannerForm.pantry_items.split(",").map((item) => item.trim()).filter(Boolean),
        budget_preference: plannerForm.budget_preference,
        max_prep_time: Number(plannerForm.max_prep_time),
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setPlannerResult(data);
      const history = await apiRequest(`/history/${profileForm.user_id}`, {}, "GET");
      setHistoryResult(history.history || []);
    });
  }

  async function runIndianLens() {
    await withLoading(async () => {
      const data = await apiRequest("/indian-intelligence", {
        user_id: profileForm.user_id,
        query: indianQuery,
        use_lmstudio: llmConfig.use_lmstudio,
        lmstudio_url: llmConfig.lmstudio_url,
        lmstudio_model: llmConfig.lmstudio_model,
      });
      setIndianResult(data);
    });
  }

  function renderTwinTab() {
    return (
      <SectionShell
        title="Personal Nutrition Twin"
        subtitle="Build a profile that powers calorie targets, explainable recommendations, and constraint-based plans."
        actions={<button onClick={saveProfile}>Save Twin</button>}
      >
        <div className="profile-grid">
          <label>
            <span>Age</span>
            <input type="number" value={profileForm.age} onChange={(event) => updateProfileField("age", Number(event.target.value))} />
          </label>
          <label>
            <span>Weight (kg)</span>
            <input type="number" value={profileForm.weight} onChange={(event) => updateProfileField("weight", Number(event.target.value))} />
          </label>
          <label>
            <span>Height (cm)</span>
            <input type="number" value={profileForm.height} onChange={(event) => updateProfileField("height", Number(event.target.value))} />
          </label>
          <label>
            <span>Gender</span>
            <select value={profileForm.gender} onChange={(event) => updateProfileField("gender", event.target.value)}>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </label>
          <label>
            <span>Activity</span>
            <select value={profileForm.activity_level} onChange={(event) => updateProfileField("activity_level", event.target.value)}>
              <option value="sedentary">Sedentary</option>
              <option value="light">Light</option>
              <option value="moderate">Moderate</option>
              <option value="active">Active</option>
              <option value="very_active">Very Active</option>
            </select>
          </label>
          <label>
            <span>Budget</span>
            <select value={profileForm.budget_preference} onChange={(event) => updateProfileField("budget_preference", event.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label>
            <span>Max Prep Time</span>
            <input type="number" value={profileForm.max_prep_time} onChange={(event) => updateProfileField("max_prep_time", Number(event.target.value))} />
          </label>
        </div>

        <div className="choice-section">
          <h3>Health Goals</h3>
          <div className="chip-group">
            {goalOptions.map((goal) => (
              <button
                key={goal.value}
                className={profileForm.health_goals.includes(goal.value) ? "chip active-chip" : "chip"}
                type="button"
                onClick={() => toggleSelection("health_goals", goal.value)}
              >
                {goal.label}
              </button>
            ))}
          </div>
        </div>

        <div className="choice-section">
          <h3>Dietary Restrictions</h3>
          <div className="chip-group">
            {restrictionOptions.map((option) => (
              <button
                key={option}
                className={profileForm.dietary_restrictions.includes(option) ? "chip active-chip" : "chip"}
                type="button"
                onClick={() => toggleSelection("dietary_restrictions", option)}
              >
                {option.replaceAll("_", " ")}
              </button>
            ))}
          </div>
        </div>

        <div className="choice-section">
          <h3>Allergies</h3>
          <div className="chip-group">
            {allergyOptions.map((option) => (
              <button
                key={option}
                className={profileForm.allergies.includes(option) ? "chip active-chip" : "chip"}
                type="button"
                onClick={() => toggleSelection("allergies", option)}
              >
                {option}
              </button>
            ))}
          </div>
        </div>

        {profileResult ? (
          <div className="result-stack">
            <MetricGrid
              items={[
                { label: "BMI", value: profileResult.metrics.bmi },
                { label: "BMR", value: `${profileResult.metrics.bmr} kcal` },
                { label: "TDEE", value: `${profileResult.metrics.tdee} kcal` },
                { label: "Target Calories", value: `${profileResult.targets.calories} kcal` },
                { label: "Protein", value: `${profileResult.targets.protein_g} g` },
                { label: "Fiber", value: `${profileResult.targets.fiber_g} g` },
              ]}
            />
            <article className="insight-panel">
              <h3>{profileResult.twin_summary.headline}</h3>
              <ul className="flat-list">
                {profileResult.twin_summary.principles.map((principle) => (
                  <li key={principle}>{principle}</li>
                ))}
              </ul>
            </article>
            <SectionShell title="Recent Coach Memory" subtitle="Your latest recommendation and planning sessions stay visible here.">
              <div className="history-list">
                {historyResult.length ? (
                  historyResult.slice().reverse().map((entry, index) => (
                    <div className="history-card" key={`${entry.type}-${index}`}>
                      <strong>{entry.type.replaceAll("_", " ")}</strong>
                      <p>{JSON.stringify(entry.payload).slice(0, 220)}...</p>
                    </div>
                  ))
                ) : (
                  <p className="muted-copy">No history yet. Save your twin and run a feature to build memory.</p>
                )}
              </div>
            </SectionShell>
          </div>
        ) : null}
      </SectionShell>
    );
  }

  function renderDiscoverTab() {
    return (
      <SectionShell
        title="Intent-Aware Nutrition Search"
        subtitle="Search by goal, nutrient, restriction, budget, or meal occasion and get ranked foods with reasons."
        actions={<button onClick={runDiscover}>Search</button>}
      >
        <textarea value={discoverQuery} onChange={(event) => setDiscoverQuery(event.target.value)} />
        {discoverResult ? (
          <div className="result-stack">
            <article className="insight-panel">
              <h3>Detected intent</h3>
              <p>Meal type: {discoverResult.intent.meal_type}</p>
              <TagList items={[...(discoverResult.intent.goals || []), ...(discoverResult.intent.nutrient_focus || []), ...(discoverResult.intent.restrictions || [])]} />
            </article>
            <article className="insight-panel">
              <h3>Indian lens</h3>
              <TagList items={discoverResult.indian_lens.detected_styles} />
              <ul className="flat-list">
                {discoverResult.indian_lens.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </article>
            {discoverResult.generated_explanation ? (
            <article className="insight-panel">
              <h3>Search insight</h3>
              <p>{discoverResult.generated_explanation}</p>
              <p className="insight-source">Dataset-backed reasoning produced from Anuvaad nutrition values and LM Studio.</p>
            </article>
          ) : null}
        <div className="food-grid">
              {discoverResult.results.map((item) => (
                <FoodCard item={item} key={item.food_name} />
              ))}
            </div>
          </div>
        ) : null}
      </SectionShell>
    );
  }

  function renderExplorerTab() {
    return (
      <SectionShell
        title="Nutrition Explorer"
        subtitle="Search any food from the dataset, inspect its nutrient profile, and compare two foods side by side."
        actions={<button onClick={runLookup}>Search Food</button>}
      >
        <div className="inline-form">
          <input value={lookupQuery} onChange={(event) => setLookupQuery(event.target.value)} placeholder="Search a food item" />
          <button onClick={runLookup} type="button">Find Details</button>
        </div>

        {lookupResult ? (
          <div className="result-stack">
            {lookupResult.generated_explanation ? (
              <article className="insight-panel">
                <h3>About {lookupResult.best_match}</h3>
                <p className="generated-copy">{lookupResult.generated_explanation}</p>
                <p className="insight-source">Source: Real nutrition data from {lookupResult.source}</p>
              </article>
            ) : null}
            <div className="source-note">
              <p><strong>Source:</strong> {lookupResult.source} • {lookupResult.results.length} close matches found</p>
            </div>
            <table className="dataset-table">
              <thead>
                <tr>
                  <th>Food Name</th>
                  <th>Calories</th>
                  <th>Protein (g)</th>
                  <th>Carbs (g)</th>
                  <th>Fat (g)</th>
                  <th>Fiber (g)</th>
                  <th>Calcium (mg)</th>
                  <th>Iron (mg)</th>
                  <th>Potassium (mg)</th>
                  <th>Serving</th>
                </tr>
              </thead>
              <tbody>
                {lookupResult.results.map((item, idx) => (
                  <tr key={idx} className={item.food_name === lookupResult.best_match ? "best-match" : ""}>
                    <td><strong>{item.food_name}</strong></td>
                    <td>{item.calories}</td>
                    <td>{item.protein_g}</td>
                    <td>{item.carbs_g}</td>
                    <td>{item.fat_g}</td>
                    <td>{item.fiber_g}</td>
                    <td>{item.calcium_mg}</td>
                    <td>{item.iron_mg}</td>
                    <td>{item.potassium_mg}</td>
                    <td>{item.serving_unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <SectionShell
          title="Food Comparison"
          subtitle="Compare two foods directly using the database values."
          actions={<button onClick={runCompare}>Compare Foods</button>}
        >
          <div className="inline-form two-up">
            <input
              value={compareForm.first}
              onChange={(event) => setCompareForm((current) => ({ ...current, first: event.target.value }))}
              placeholder="First food"
            />
            <input
              value={compareForm.second}
              onChange={(event) => setCompareForm((current) => ({ ...current, second: event.target.value }))}
              placeholder="Second food"
            />
          </div>

          {compareResult?.comparison ? (
            <div className="result-stack">
              {compareResult.generated_explanation ? (
                <article className="insight-panel">
                  <h3>AI Comparison Insight</h3>
                  <p className="generated-copy">{compareResult.generated_explanation}</p>
                </article>
              ) : null}
              <div className="compare-grid">
                {[compareResult.comparison.first_food, compareResult.comparison.second_food].map((food) => (
                  <article className="plan-card" key={food.food_name}>
                    <h3>{food.food_name}</h3>
                    <MetricGrid
                      items={[
                        { label: "Calories", value: food.calories },
                        { label: "Protein", value: `${food.protein_g} g` },
                        { label: "Carbs", value: `${food.carbs_g} g` },
                        { label: "Fat", value: `${food.fat_g} g` },
                        { label: "Fiber", value: `${food.fiber_g} g` },
                      ]}
                    />
                  </article>
                ))}
              </div>
              <article className="insight-panel">
                <h3>Comparison Summary</h3>
                <ul className="flat-list">
                  {compareResult.comparison.summary.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </article>
            </div>
          ) : compareResult?.message ? <p className="muted-copy">{compareResult.message}</p> : null}
        </SectionShell>
      </SectionShell>
    );
  }

  function renderRepairTab() {
    return (
      <SectionShell
        title="Meal Repair Mode"
        subtitle="Drop in a real meal and NutriWise will break it down, flag imbalances, and suggest practical upgrades."
        actions={<button onClick={runRepair}>Repair Meal</button>}
      >
        <textarea value={repairQuery} onChange={(event) => setRepairQuery(event.target.value)} />
        {repairResult ? (
          <div className="result-stack">
            <MetricGrid
              items={[
                { label: "Calories", value: repairResult.meal_totals.calories },
                { label: "Protein", value: `${repairResult.meal_totals.protein_g} g` },
                { label: "Carbs", value: `${repairResult.meal_totals.carbs_g} g` },
                { label: "Fat", value: `${repairResult.meal_totals.fat_g} g` },
                { label: "Fiber", value: `${repairResult.meal_totals.fiber_g} g` },
              ]}
            />
            {repairResult.generated_explanation ? (
              <article className="insight-panel">
                <h3>Repair summary</h3>
                <p>{repairResult.generated_explanation}</p>
                <p className="insight-source">Grounded in dataset-derived meal totals and matched food nutrients.</p>
              </article>
            ) : null}
            <article className="insight-panel">
              <h3>{repairResult.assessment}</h3>
              <ul className="flat-list">
                {repairResult.issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </article>
            <div className="card-grid">
              {repairResult.upgrades.map((upgrade) => (
                <article className="mini-card" key={upgrade.type}>
                  <strong>{upgrade.type.replaceAll("_", " ")}</strong>
                  <p>{upgrade.suggestion}</p>
                </article>
              ))}
            </div>
            <div className="food-grid">
              {repairResult.matched_foods.map((food) => (
                <article className="mini-card" key={food.food_name}>
                  <strong>{food.food_name}</strong>
                  <p>{food.calories} kcal • {food.protein_g} g protein • {food.fiber_g} g fiber</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </SectionShell>
    );
  }

  function renderRecommendTab() {
    return (
      <SectionShell
        title="Explainable Recommendations"
        subtitle="Move beyond generic suggestions and show exactly why each food fits the user profile."
        actions={<button onClick={runRecommendations}>Generate</button>}
      >
        <div className="inline-form">
          <select value={recommendForm.meal_type} onChange={(event) => setRecommendForm((current) => ({ ...current, meal_type: event.target.value }))}>
            <option value="breakfast">Breakfast</option>
            <option value="lunch">Lunch</option>
            <option value="dinner">Dinner</option>
            <option value="snacks">Snacks</option>
            <option value="general">General</option>
          </select>
          <input
            value={recommendForm.query}
            onChange={(event) => setRecommendForm((current) => ({ ...current, query: event.target.value }))}
            placeholder="high iron vegetarian lunch"
          />
        </div>
        {recommendResult ? (
          <div className="result-stack">
            <article className="insight-panel">
              <h3>{recommendResult.summary}</h3>
              <TagList items={recommendResult.profile_snapshot.health_goals} />
              {recommendResult.generated_explanation ? (
                <>
                  <p>{recommendResult.generated_explanation}</p>
                  <p className="insight-source">Based on dataset nutrition values and LM Studio summarization.</p>
                </>
              ) : null}
            </article>
            <div className="food-grid">
              {recommendResult.recommendations.map((item) => (
                <FoodCard item={item} key={item.food_name} />
              ))}
            </div>
          </div>
        ) : null}
      </SectionShell>
    );
  }

  function renderPlannerTab() {
    return (
      <SectionShell
        title="Constraint-Based Smart Meal Planner"
        subtitle="Plan a day around budget, pantry, prep-time, and profile targets instead of generating generic text."
        actions={<button onClick={runPlanner}>Build Day Plan</button>}
      >
        <div className="planner-grid">
          <label>
            <span>Planning focus</span>
            <input value={plannerForm.query} onChange={(event) => setPlannerForm((current) => ({ ...current, query: event.target.value }))} />
          </label>
          <label>
            <span>Pantry items</span>
            <input value={plannerForm.pantry_items} onChange={(event) => setPlannerForm((current) => ({ ...current, pantry_items: event.target.value }))} />
          </label>
          <label>
            <span>Budget</span>
            <select value={plannerForm.budget_preference} onChange={(event) => setPlannerForm((current) => ({ ...current, budget_preference: event.target.value }))}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label>
            <span>Max Prep Time</span>
            <input type="number" value={plannerForm.max_prep_time} onChange={(event) => setPlannerForm((current) => ({ ...current, max_prep_time: Number(event.target.value) }))} />
          </label>
        </div>
        {plannerResult ? (
          <div className="result-stack">
            {plannerResult.generated_explanation ? (
              <article className="insight-panel">
                <h3>Plan overview</h3>
                <p>{plannerResult.generated_explanation}</p>
                <p className="insight-source">Built from dataset-selected foods and a grounded nutrition summary.</p>
              </article>
            ) : null}
            <MetricGrid
              items={[
                { label: "Daily Calories", value: plannerResult.daily_estimate.calories },
                { label: "Protein", value: `${plannerResult.daily_estimate.protein_g} g` },
                { label: "Carbs", value: `${plannerResult.daily_estimate.carbs_g} g` },
                { label: "Fat", value: `${plannerResult.daily_estimate.fat_g} g` },
                { label: "Fiber", value: `${plannerResult.daily_estimate.fiber_g} g` },
              ]}
            />
            <div className="plan-grid">
              {Object.entries(plannerResult.meals).map(([mealType, meal]) => (
                <article className="plan-card" key={mealType}>
                  <h3>{mealType}</h3>
                  <p>{meal.notes}</p>
                  <p>Target: {meal.target_calories} kcal</p>
                  {meal.items.map((item) => (
                    <div className="plan-item" key={`${mealType}-${item.food_name}`}>
                      <strong>{item.food_name}</strong>
                      <span>{item.calories} kcal • {item.protein_g} g protein</span>
                    </div>
                  ))}
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </SectionShell>
    );
  }

  function renderIndianTab() {
    return (
      <SectionShell
        title="Indian Food Intelligence"
        subtitle="Interpret meals in an Indian context, detect cuisine style, and suggest smarter swaps without losing familiarity."
        actions={<button onClick={runIndianLens}>Analyze Indian Meal</button>}
      >
        <textarea value={indianQuery} onChange={(event) => setIndianQuery(event.target.value)} />
        {indianResult ? (
          <div className="result-stack">
            {indianResult.generated_explanation ? (
              <article className="insight-panel">
                <h3>Indian lens summary</h3>
                <p>{indianResult.generated_explanation}</p>
                <p className="insight-source">Uses dataset matches and LM Studio to explain Indian food recommendations.</p>
              </article>
            ) : null}
            <article className="insight-panel">
              <h3>Detected styles</h3>
              <TagList items={indianResult.lens.detected_styles} />
              <ul className="flat-list">
                {indianResult.lens.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </article>
            <div className="card-grid">
              {indianResult.smart_swaps.map((swap) => (
                <article className="mini-card" key={`${swap.from}-${swap.to}`}>
                  <strong>{swap.from} → {swap.to}</strong>
                  <p>{swap.why}</p>
                </article>
              ))}
            </div>
            <div className="food-grid">
              {indianResult.recommended_foods.map((item) => (
                <FoodCard item={item} key={item.food_name} />
              ))}
            </div>
          </div>
        ) : null}
      </SectionShell>
    );
  }

  function renderActiveTab() {
    if (activeTab === "twin") return renderTwinTab();
    if (activeTab === "explorer") return renderExplorerTab();
    if (activeTab === "discover") return renderDiscoverTab();
    if (activeTab === "repair") return renderRepairTab();
    if (activeTab === "recommend") return renderRecommendTab();
    if (activeTab === "planner") return renderPlannerTab();
    return renderIndianTab();
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">NutriWise</p>
        <h1>Data-Driven Nutrition Coach for Real Indian Meals</h1>
        <p className="hero-copy">
          Personalized nutrition twins, intent-aware food search, explainable recommendations, meal repair, and
          smart day planning built on your nutrition dataset.
        </p>
      </header>

      <main className="layout">
        <SettingsPanel
          settings={settings}
          llmConfig={llmConfig}
          onConfigChange={(field, value) => setLlmConfig((current) => ({ ...current, [field]: value }))}
          onLoadProfile={loadProfile}
        />

        <section className="workspace">
          <nav className="tab-row">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={tab.id === activeTab ? "tab active" : "tab"}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {loading ? <p className="status-banner">NutriWise is thinking through your profile and dataset...</p> : null}
          {error ? <p className="error-banner">{error}</p> : null}
          {renderActiveTab()}
        </section>
      </main>
    </div>
  );
}

export default App;
