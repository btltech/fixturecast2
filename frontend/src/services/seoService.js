/**
 * SEO Service
 * Generates optimized meta tags, structured data, and share images for predictions
 */

import { BACKEND_API_URL, APP_URL } from "../config.js";

/**
 * Generate SEO metadata for a prediction page
 */
export function generatePredictionSEO(fixture, prediction) {
  const homeTeam = fixture.teams?.home?.name || "Home Team";
  const awayTeam = fixture.teams?.away?.name || "Away Team";
  const league = fixture.league?.name || "League";
  const date = new Date(fixture.fixture?.date);
  const dateStr = date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  // Generate title (max 60 chars for Google)
  const title = `${homeTeam} vs ${awayTeam} Prediction - ${dateStr} | FixtureCast`;

  // Generate description (max 160 chars for Google)
  let description = `AI prediction for ${homeTeam} vs ${awayTeam} on ${dateStr}. `;

  if (prediction) {
    const homeProb = (prediction.home_win_prob * 100).toFixed(0);
    const awayProb = (prediction.away_win_prob * 100).toFixed(0);
    const drawProb = (prediction.draw_prob * 100).toFixed(0);
    const score = prediction.predicted_scoreline || "N/A";

    description += `Predicted score: ${score}. Win probabilities: ${homeTeam} ${homeProb}%, Draw ${drawProb}%, ${awayTeam} ${awayProb}%.`;
  }

  // Truncate description if too long
  if (description.length > 160) {
    description = description.substring(0, 157) + "...";
  }

  // Generate OG image URL (we'll create this endpoint)
  const fixtureId = fixture.fixture?.id;
  const leagueId = fixture.league?.id || 39;
  const imageUrl = `${BACKEND_API_URL}/api/og-image/${fixtureId}?league=${leagueId}`;

  // Page URL
  const url = `${APP_URL}/prediction/${fixtureId}?league=${leagueId}`;

  // Generate Schema.org structured data
  const schema = generatePredictionSchema(fixture, prediction);

  return {
    title,
    description,
    image: imageUrl,
    url,
    type: "article",
    schema,
    keywords: generateKeywords(homeTeam, awayTeam, league),
  };
}

/**
 * Generate Schema.org structured data for prediction
 * https://schema.org/SportsEvent
 */
export function generatePredictionSchema(fixture, prediction) {
  const homeTeam = fixture.teams?.home?.name || "Home Team";
  const awayTeam = fixture.teams?.away?.name || "Away Team";
  const league = fixture.league?.name || "League";
  const venue = fixture.fixture?.venue?.name || "Stadium";
  const date = fixture.fixture?.date;

  const schema = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: `${homeTeam} vs ${awayTeam}`,
    description: `${league} match between ${homeTeam} and ${awayTeam}`,
    startDate: date,
    location: {
      "@type": "Place",
      name: venue,
    },
    homeTeam: {
      "@type": "SportsTeam",
      name: homeTeam,
      logo: fixture.teams?.home?.logo,
    },
    awayTeam: {
      "@type": "SportsTeam",
      name: awayTeam,
      logo: fixture.teams?.away?.logo,
    },
    sport: "Soccer",
    competitionCategory: league,
  };

  // Add prediction as additional metadata
  if (prediction) {
    schema.additionalProperty = [
      {
        "@type": "PropertyValue",
        name: "AI Predicted Score",
        value: prediction.predicted_scoreline,
      },
      {
        "@type": "PropertyValue",
        name: "Home Win Probability",
        value: `${(prediction.home_win_prob * 100).toFixed(1)}%`,
      },
      {
        "@type": "PropertyValue",
        name: "Draw Probability",
        value: `${(prediction.draw_prob * 100).toFixed(1)}%`,
      },
      {
        "@type": "PropertyValue",
        name: "Away Win Probability",
        value: `${(prediction.away_win_prob * 100).toFixed(1)}%`,
      },
    ];
  }

  return schema;
}

/**
 * Generate SEO keywords
 */
function generateKeywords(homeTeam, awayTeam, league) {
  return [
    `${homeTeam} vs ${awayTeam} prediction`,
    `${homeTeam} ${awayTeam} AI prediction`,
    `${league} predictions`,
    `${homeTeam} prediction`,
    `${awayTeam} prediction`,
    "football predictions",
    "soccer betting tips",
    "match predictions AI",
    "football AI",
  ].join(", ");
}

/**
 * Generate SEO for today's fixtures page
 */
export function generateFixturesSEO() {
  const today = new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return {
    title: `Today's Football Predictions - ${today} | FixtureCast`,
    description: `AI-powered predictions for all football matches today (${today}). Get win probabilities, predicted scores, and detailed analysis for Premier League, La Liga, Serie A, and more.`,
    image: `${BACKEND_API_URL}/api/og-image/daily`,
    url: `${APP_URL}/fixtures`,
    type: "website",
    keywords:
      "today's football predictions, soccer predictions today, AI football predictions, betting tips, match predictions",
  };
}

/**
 * Generate SEO for homepage
 */
export function generateHomeSEO() {
  return {
    title: "FixtureCast - AI-Powered Football Match Predictions",
    description:
      "Get accurate AI predictions for football matches across Premier League, La Liga, Serie A, Bundesliga, and more. 8-model ensemble trained on 5 seasons of data. Free predictions updated daily.",
    image: `${BACKEND_API_URL}/api/og-image/home`,
    url: APP_URL,
    type: "website",
    keywords:
      "football predictions, soccer predictions, AI predictions, Premier League predictions, match predictions, betting tips, football AI",
    schema: {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: "FixtureCast",
      description: "AI-powered football match predictions",
      url: APP_URL,
      potentialAction: {
        "@type": "SearchAction",
        target: `${APP_URL}/search?q={search_term_string}`,
        "query-input": "required name=search_term_string",
      },
    },
  };
}

/**
 * Generate SEO-friendly URL slug
 */
export function generateSlug(homeTeam, awayTeam, date) {
  const dateStr = new Date(date).toISOString().split("T")[0]; // YYYY-MM-DD
  const slug = `${homeTeam}-vs-${awayTeam}-${dateStr}`
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return slug;
}
