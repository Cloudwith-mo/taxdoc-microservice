import { TextractClient, AnalyzeDocumentCommand } from "@aws-sdk/client-textract";

const client = new TextractClient({ region: process.env.AWS_REGION });

const QUERIES = [
  { Text: "What is the employee name?", Alias: "employee_name" },
  { Text: "What is the employer name?", Alias: "employer_name" },
  { Text: "What is the pay period start date?", Alias: "pay_period_start" },
  { Text: "What is the pay period end date?", Alias: "pay_period_end" },
  { Text: "What is the pay date?", Alias: "pay_date" },
  { Text: "What is the net pay for the current period?", Alias: "net_pay_current" },
  { Text: "What is the gross pay for the current period?", Alias: "gross_pay_current" },
  { Text: "What is the gross pay year to date?", Alias: "gross_pay_ytd" },
  { Text: "What is the net pay year to date?", Alias: "net_pay_ytd" },
  { Text: "What are the total deductions for current period?", Alias: "deductions_current" }
];

export const handler = async (event) => {
  const { s3Bucket, s3Key } = JSON.parse(event.body);
  
  const cmd = new AnalyzeDocumentCommand({
    Document: { S3Object: { Bucket: s3Bucket, Name: s3Key } },
    FeatureTypes: ["FORMS", "TABLES", "QUERIES"],
    QueriesConfig: { Queries: QUERIES }
  });
  
  const res = await client.send(cmd);

  // Extract query answers with confidence and bounding boxes
  const fields = {};
  const line_items = { earnings: [], deductions: [] };
  
  for (const b of res.Blocks ?? []) {
    if (b.BlockType === "QUERY_RESULT" && b.Query) {
      fields[b.Query.Alias] = {
        value: b.Text?.trim() ?? null,
        confidence: (b.Confidence ?? 0) / 100,
        bbox: b.Geometry?.BoundingBox ?? null,
        source: "textract_query"
      };
    }
  }

  // Parse TABLE blocks for earnings/deductions
  for (const b of res.Blocks ?? []) {
    if (b.BlockType === "TABLE") {
      const table = parseTable(res.Blocks, b);
      categorizeLineItems(table, line_items);
    }
  }

  // Validation and needs_review logic
  const needs_review = validatePaystub(fields);
  
  const classification = {
    type: "PAYSTUB",
    confidence: calculateOverallConfidence(fields)
  };

  return {
    statusCode: 200,
    body: JSON.stringify({
      classification,
      fields,
      line_items,
      needs_review
    })
  };
};

function parseTable(blocks, tableBlock) {
  const cells = {};
  const blockMap = {};
  
  blocks.forEach(block => {
    blockMap[block.Id] = block;
  });
  
  // Get table cells
  if (tableBlock.Relationships) {
    tableBlock.Relationships.forEach(relationship => {
      if (relationship.Type === "CHILD") {
        relationship.Ids.forEach(childId => {
          const cell = blockMap[childId];
          if (cell && cell.BlockType === "CELL") {
            const row = cell.RowIndex;
            const col = cell.ColumnIndex;
            if (!cells[row]) cells[row] = {};
            cells[row][col] = getCellText(blocks, cell);
          }
        });
      }
    });
  }
  
  return cells;
}

function getCellText(blocks, cell) {
  let text = "";
  if (cell.Relationships) {
    cell.Relationships.forEach(relationship => {
      if (relationship.Type === "CHILD") {
        relationship.Ids.forEach(childId => {
          const child = blocks.find(b => b.Id === childId);
          if (child && child.Text) {
            text += child.Text + " ";
          }
        });
      }
    });
  }
  return text.trim();
}

function categorizeLineItems(table, line_items) {
  Object.keys(table).forEach(rowKey => {
    const row = table[rowKey];
    const firstCol = row[1] || "";
    
    if (firstCol.toLowerCase().includes("regular") || 
        firstCol.toLowerCase().includes("overtime") ||
        firstCol.toLowerCase().includes("bonus")) {
      line_items.earnings.push({
        type: firstCol,
        amount_current: parseFloat((row[2] || "0").replace(/[^0-9.-]/g, "")) || 0,
        amount_ytd: parseFloat((row[3] || "0").replace(/[^0-9.-]/g, "")) || 0
      });
    } else if (firstCol.toLowerCase().includes("tax") ||
               firstCol.toLowerCase().includes("insurance") ||
               firstCol.toLowerCase().includes("401k")) {
      line_items.deductions.push({
        type: firstCol,
        amount_current: parseFloat((row[2] || "0").replace(/[^0-9.-]/g, "")) || 0,
        amount_ytd: parseFloat((row[3] || "0").replace(/[^0-9.-]/g, "")) || 0
      });
    }
  });
}

function validatePaystub(fields) {
  let needs_review = false;
  
  // Check confidence thresholds
  Object.values(fields).forEach(field => {
    if (field.confidence < 0.6) {
      needs_review = true;
    }
  });
  
  // Math validation: gross - deductions ≈ net
  const gross = parseFloat(fields.gross_pay_current?.value?.replace(/[^0-9.-]/g, "") || "0");
  const net = parseFloat(fields.net_pay_current?.value?.replace(/[^0-9.-]/g, "") || "0");
  const deductions = parseFloat(fields.deductions_current?.value?.replace(/[^0-9.-]/g, "") || "0");
  
  if (Math.abs(gross - deductions - net) > 0.01) {
    needs_review = true;
  }
  
  return needs_review;
}

function calculateOverallConfidence(fields) {
  const confidences = Object.values(fields).map(f => f.confidence).filter(c => c > 0);
  return confidences.length > 0 ? confidences.reduce((a, b) => a + b) / confidences.length : 0;
}