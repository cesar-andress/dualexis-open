// DUALEXIS Semantic Safety Graph — Neo4j conceptual model (identity-free)
// See docs/safety_graph.md for full documentation.

// --- Constraints ---
CREATE CONSTRAINT location_id IF NOT EXISTS
FOR (l:Location) REQUIRE l.location_id IS UNIQUE;

CREATE CONSTRAINT zone_id IF NOT EXISTS
FOR (z:Zone) REQUIRE z.zone_id IS UNIQUE;

CREATE CONSTRAINT exit_id IF NOT EXISTS
FOR (x:Exit) REQUIRE x.exit_id IS UNIQUE;

CREATE CONSTRAINT event_id IF NOT EXISTS
FOR (e:SafetyEvent) REQUIRE e.event_id IS UNIQUE;

CREATE CONSTRAINT recommendation_id IF NOT EXISTS
FOR (r:OrchestrationRecommendation) REQUIRE r.recommendation_id IS UNIQUE;

// --- Spatial topology ---
MERGE (loc:Location {location_id: 'site-north-hall', label: 'North Building'})

MERGE (z1:Zone {zone_id: 'z-hall-a', zone_label: 'Hallway A'})
MERGE (z2:Zone {zone_id: 'z-cafeteria', zone_label: 'Cafeteria'})
MERGE (z3:Zone {zone_id: 'z-exit-lobby', zone_label: 'Exit Lobby'})

MERGE (loc)-[:CONTAINS]->(z1)
MERGE (loc)-[:CONTAINS]->(z2)
MERGE (loc)-[:CONTAINS]->(z3)

MERGE (z1)-[:ADJACENT_TO {distance_band: 'immediate'}]->(z2)
MERGE (z2)-[:ADJACENT_TO {distance_band: 'immediate'}]->(z1)
MERGE (z2)-[:ADJACENT_TO {distance_band: 'immediate'}]->(z3)

MERGE (ex:Exit {exit_id: 'exit-a-north', exit_type: 'emergency', is_emergency: true})
MERGE (z1)-[:HAS_EXIT]->(ex)
MERGE (ex)-[:CONNECTS_TO {direction: 'outbound'}]->(:Zone {zone_id: 'exterior-north', zone_label: 'Exterior North'});

// --- Events ---
MERGE (e1:SafetyEvent {
  event_id: 'e-001',
  event_type: 'acoustic_anomaly',
  severity: 'medium',
  confidence: 0.71,
  explanation: 'Impact-like acoustic pattern detected.',
  timestamp: datetime('2026-05-25T14:30:12Z')
})
WITH e1
MATCH (z1:Zone {zone_id: 'z-hall-a'})
MERGE (e1)-[:OCCURRED_IN]->(z1);

MERGE (e2:SafetyEvent {
  event_id: 'e-002',
  event_type: 'crowd_activity',
  severity: 'medium',
  confidence: 0.74,
  explanation: 'Elevated aggregate density; identity-free estimate.',
  timestamp: datetime('2026-05-25T14:30:45Z')
})
WITH e2
MATCH (z2:Zone {zone_id: 'z-cafeteria'})
MERGE (e2)-[:OCCURRED_IN]->(z2);

MATCH (e1:SafetyEvent {event_id: 'e-001'}), (e2:SafetyEvent {event_id: 'e-002'})
MERGE (e1)-[:FOLLOWED_BY {delta_ms: 33000}]->(e2)
MERGE (e1)-[:CORROBORATED_BY {modality: 'multimodal'}]->(e2);

MATCH (e1:SafetyEvent {event_id: 'e-001'}), (z2:Zone {zone_id: 'z-cafeteria'})
MERGE (e1)-[:PROPAGATES_RISK_TO {alpha: 0.6, lambda: 0.05, score: 0.42}]->(z2);

// --- Orchestration recommendation ---
MATCH (e2:SafetyEvent {event_id: 'e-002'}), (z2:Zone {zone_id: 'z-cafeteria'})
MERGE (rec:OrchestrationRecommendation {
  recommendation_id: 'rec-001',
  action: 'request_review',
  explanation: 'Correlated acoustic and crowd events in adjacent zones.',
  requires_human_approval: true,
  confidence: 0.68
})
MERGE (e2)-[:TRIGGERS {confidence: 0.68}]->(rec)
MERGE (rec)-[:ADVISES_FOR]->(z2);
