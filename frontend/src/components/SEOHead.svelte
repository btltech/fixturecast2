import { onMount } from "svelte";

export let data = {};

// SEO metadata
$: title = data.title || "FixtureCast";
$: description = data.description || "AI-powered football match predictions";
$: image = data.image || `${window.location.origin}/default-og.png`;
$: url = data.url || window.location.href;
$: type = data.type || "website";
$: schema = data.schema || null;

onMount(() => {
  if (typeof window !== "undefined") {
    updateMetaTags();
  }
});

function updateMetaTags() {
  // Update title
  document.title = title;

  // Update or create meta tags
  updateOrCreateMeta("description", description);

  // Open Graph
  updateOrCreateMeta("og:title", title, "property");
  updateOrCreateMeta("og:description", description, "property");
  updateOrCreateMeta("og:image", image, "property");
  updateOrCreateMeta("og:url", url, "property");
  updateOrCreateMeta("og:type", type, "property");
  updateOrCreateMeta("og:site_name", "FixtureCast", "property");

  // Twitter Card
  updateOrCreateMeta("twitter:card", "summary_large_image");
  updateOrCreateMeta("twitter:title", title);
  updateOrCreateMeta("twitter:description", description);
  updateOrCreateMeta("twitter:image", image);

  // Canonical URL
  updateOrCreateLink("canonical", url);

  // Schema.org structured data
  if (schema) {
    updateOrCreateSchema(schema);
  }
}

function updateOrCreateMeta(name, content, attribute = "name") {
  let meta = document.querySelector(`meta[${attribute}="${name}"]`);
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute(attribute, name);
    document.head.appendChild(meta);
  }
  meta.setAttribute("content", content);
}

function updateOrCreateLink(rel, href) {
  let link = document.querySelector(`link[rel="${rel}"]`);
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", rel);
    document.head.appendChild(link);
  }
  link.setAttribute("href", href);
}

function updateOrCreateSchema(schemaData) {
  let script = document.querySelector('script[type="application/ld+json"]#prediction-schema');
  if (!script) {
    script = document.createElement("script");
    script.setAttribute("type", "application/ld+json");
    script.setAttribute("id", "prediction-schema");
    document.head.appendChild(script);
  }
  script.textContent = JSON.stringify(schemaData, null, 2);
}

// Watch for data changes and update meta tags
$: if (title) updateMetaTags();
