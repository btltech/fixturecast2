export function exportPredictionsToCSV(predictions) {
  const headers = [
    "Date",
    "Home Team",
    "Away Team",
    "Home Win %",
    "Draw %",
    "Away Win %",
    "Predicted Score",
    "BTTS %",
    "Over 2.5 %",
    "Confidence",
  ];

  const rows = predictions.map((pred) => [
    pred.date || new Date().toLocaleDateString(),
    pred.home_team || "",
    pred.away_team || "",
    ((pred.home_win_prob || 0) * 100).toFixed(1),
    ((pred.draw_prob || 0) * 100).toFixed(1),
    ((pred.away_win_prob || 0) * 100).toFixed(1),
    pred.predicted_scoreline || "",
    ((pred.btts_prob || 0) * 100).toFixed(1),
    ((pred.over25_prob || 0) * 100).toFixed(1),
    ((pred.confidence || 0) * 100).toFixed(1),
  ]);

  const csvContent = [
    headers.join(","),
    ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute(
    "download",
    `fixturecast_predictions_${new Date().toISOString().split("T")[0]}.csv`,
  );
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function exportPredictionsToPDF(predictions) {
  // Create a printable HTML page
  const content = `
<!DOCTYPE html>
<html>
<head>
  <title>FixtureCast Predictions</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; }
    h1 { color: #8b5cf6; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th { background: #8b5cf6; color: white; padding: 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #ddd; }
    tr:hover { background: #f5f5f5; }
    .footer { margin-top: 30px; font-size: 12px; color: #666; }
  </style>
</head>
<body>
  <h1>FixtureCast AI Predictions</h1>
  <p>Generated: ${new Date().toLocaleString()}</p>
  <table>
    <thead>
      <tr>
        <th>Match</th>
        <th>Home Win</th>
        <th>Draw</th>
        <th>Away Win</th>
        <th>Score</th>
        <th>Confidence</th>
      </tr>
    </thead>
    <tbody>
      ${predictions
        .map(
          (pred) => `
        <tr>
          <td>${pred.home_team} vs ${pred.away_team}</td>
          <td>${((pred.home_win_prob || 0) * 100).toFixed(1)}%</td>
          <td>${((pred.draw_prob || 0) * 100).toFixed(1)}%</td>
          <td>${((pred.away_win_prob || 0) * 100).toFixed(1)}%</td>
          <td>${pred.predicted_scoreline || "N/A"}</td>
          <td>${((pred.confidence || 0) * 100).toFixed(0)}%</td>
        </tr>
      `,
        )
        .join("")}
    </tbody>
  </table>
  <div class="footer">
    <p>FixtureCast ML - AI-Powered Football Predictions</p>
    <p>Predictions generated using ensemble of 11 machine learning models</p>
  </div>
</body>
</html>
  `;

  const printWindow = window.open("", "_blank");

  // Handle popup blocker
  if (!printWindow) {
    alert(
      "Please allow popups to export PDF. Check your browser's popup blocker settings.",
    );
    return;
  }

  printWindow.document.write(content);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 250);
}
