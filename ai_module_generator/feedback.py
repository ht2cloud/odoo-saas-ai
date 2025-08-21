"""
Continuous Learning & Feedback Loop

Collects user feedback after module generation/deployment and helps
retrain AI models for better future outputs.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class FeedbackType(Enum):
    """Types of feedback"""
    RATING = "rating"
    SUGGESTION = "suggestion"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    USAGE_DATA = "usage_data"


class Rating(Enum):
    """Feedback ratings"""
    EXCELLENT = 5
    GOOD = 4
    AVERAGE = 3
    POOR = 2
    TERRIBLE = 1


@dataclass
class FeedbackEntry:
    """Individual feedback entry"""
    id: Optional[str] = None
    user_id: str = ""
    module_name: str = ""
    feedback_type: FeedbackType = FeedbackType.RATING
    rating: Optional[Rating] = None
    content: str = ""
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    processed: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UsageMetrics:
    """Module usage metrics"""
    module_name: str
    installs: int = 0
    uninstalls: int = 0
    active_users: int = 0
    feature_usage: Dict[str, int] = None
    error_count: int = 0
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.feature_usage is None:
            self.feature_usage = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}


@dataclass
class LearningInsight:
    """Insights derived from feedback analysis"""
    category: str
    description: str
    confidence: float
    recommendations: List[str]
    affected_components: List[str]
    priority: str  # low, medium, high, critical


class FeedbackCollector:
    """
    Collects and analyzes user feedback to improve AI model performance.
    """
    
    def __init__(self, db_path: str = "feedback.db"):
        """
        Initialize feedback collector.
        
        Args:
            db_path: Path to SQLite database for storing feedback
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for feedback storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        module_name TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        rating INTEGER,
                        content TEXT,
                        metadata TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        processed BOOLEAN DEFAULT FALSE
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usage_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        module_name TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_value REAL,
                        metadata TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS learning_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        description TEXT NOT NULL,
                        confidence REAL,
                        recommendations TEXT,
                        affected_components TEXT,
                        priority TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        applied BOOLEAN DEFAULT FALSE
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
    
    def collect_feedback(self, feedback: FeedbackEntry) -> bool:
        """
        Collect user feedback.
        
        Args:
            feedback: Feedback entry to store
            
        Returns:
            True if feedback was stored successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO feedback 
                    (user_id, module_name, feedback_type, rating, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback.user_id,
                    feedback.module_name,
                    feedback.feedback_type.value,
                    feedback.rating.value if feedback.rating else None,
                    feedback.content,
                    json.dumps(feedback.metadata),
                    feedback.timestamp
                ))
                conn.commit()
                
            self.logger.info(f"Feedback collected for module {feedback.module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to collect feedback: {e}")
            return False
    
    def collect_usage_metrics(self, metrics: UsageMetrics) -> bool:
        """
        Collect module usage metrics.
        
        Args:
            metrics: Usage metrics to store
            
        Returns:
            True if metrics were stored successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store various metrics
                metric_data = [
                    ("installs", metrics.installs),
                    ("uninstalls", metrics.uninstalls),
                    ("active_users", metrics.active_users),
                    ("error_count", metrics.error_count)
                ]
                
                for metric_type, value in metric_data:
                    conn.execute("""
                        INSERT INTO usage_metrics 
                        (module_name, metric_type, metric_value, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (
                        metrics.module_name,
                        metric_type,
                        value,
                        json.dumps({
                            "feature_usage": metrics.feature_usage,
                            "performance_metrics": metrics.performance_metrics
                        })
                    ))
                
                conn.commit()
                
            self.logger.info(f"Usage metrics collected for module {metrics.module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to collect usage metrics: {e}")
            return False
    
    def get_feedback_summary(self, module_name: Optional[str] = None,
                           days: int = 30) -> Dict[str, Any]:
        """
        Get summary of feedback for analysis.
        
        Args:
            module_name: Optional module name filter
            days: Number of days to look back
            
        Returns:
            Feedback summary statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                where_clause = "WHERE timestamp >= ?"
                params = [cutoff_date]
                
                if module_name:
                    where_clause += " AND module_name = ?"
                    params.append(module_name)
                
                # Get rating distribution
                cursor = conn.execute(f"""
                    SELECT rating, COUNT(*) as count
                    FROM feedback 
                    {where_clause} AND rating IS NOT NULL
                    GROUP BY rating
                """, params)
                
                rating_distribution = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get feedback by type
                cursor = conn.execute(f"""
                    SELECT feedback_type, COUNT(*) as count
                    FROM feedback 
                    {where_clause}
                    GROUP BY feedback_type
                """, params)
                
                feedback_by_type = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get average rating
                cursor = conn.execute(f"""
                    SELECT AVG(rating) as avg_rating
                    FROM feedback 
                    {where_clause} AND rating IS NOT NULL
                """, params)
                
                avg_rating = cursor.fetchone()[0] or 0
                
                # Get total feedback count
                cursor = conn.execute(f"""
                    SELECT COUNT(*) as total
                    FROM feedback 
                    {where_clause}
                """, params)
                
                total_feedback = cursor.fetchone()[0]
                
                return {
                    "total_feedback": total_feedback,
                    "average_rating": round(avg_rating, 2),
                    "rating_distribution": rating_distribution,
                    "feedback_by_type": feedback_by_type,
                    "period_days": days
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get feedback summary: {e}")
            return {}
    
    def analyze_feedback_patterns(self, module_name: Optional[str] = None) -> List[LearningInsight]:
        """
        Analyze feedback patterns to generate learning insights.
        
        Args:
            module_name: Optional module name filter
            
        Returns:
            List of learning insights
        """
        insights = []
        
        try:
            # Get recent feedback
            feedback_summary = self.get_feedback_summary(module_name, days=90)
            
            if not feedback_summary:
                return insights
            
            # Analyze rating trends
            if feedback_summary["average_rating"] < 3.0:
                insights.append(LearningInsight(
                    category="quality",
                    description="Low average rating indicates quality issues",
                    confidence=0.8,
                    recommendations=[
                        "Review code generation templates",
                        "Improve validation rules",
                        "Enhance error handling"
                    ],
                    affected_components=["code_generator", "nlp_parser"],
                    priority="high"
                ))
            
            # Analyze feedback types
            feedback_types = feedback_summary.get("feedback_by_type", {})
            
            if feedback_types.get("bug_report", 0) > 5:
                insights.append(LearningInsight(
                    category="reliability",
                    description="High number of bug reports",
                    confidence=0.9,
                    recommendations=[
                        "Increase test coverage",
                        "Add more validation checks",
                        "Review common error patterns"
                    ],
                    affected_components=["code_generator", "integration"],
                    priority="high"
                ))
            
            if feedback_types.get("feature_request", 0) > 3:
                insights.append(LearningInsight(
                    category="functionality",
                    description="Multiple feature requests indicate gaps",
                    confidence=0.7,
                    recommendations=[
                        "Analyze requested features",
                        "Prioritize common requests",
                        "Expand NLP understanding"
                    ],
                    affected_components=["nlp_parser", "config_engine"],
                    priority="medium"
                ))
            
            # Analyze specific feedback content
            content_insights = self._analyze_feedback_content(module_name)
            insights.extend(content_insights)
            
            # Store insights for future reference
            for insight in insights:
                self._store_learning_insight(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to analyze feedback patterns: {e}")
            return insights
    
    def _analyze_feedback_content(self, module_name: Optional[str] = None) -> List[LearningInsight]:
        """Analyze feedback content for patterns"""
        insights = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                where_clause = "WHERE content IS NOT NULL AND content != ''"
                params = []
                
                if module_name:
                    where_clause += " AND module_name = ?"
                    params.append(module_name)
                
                cursor = conn.execute(f"""
                    SELECT content, feedback_type, rating
                    FROM feedback 
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, params)
                
                feedback_entries = cursor.fetchall()
                
                # Analyze common themes
                themes = self._extract_themes(feedback_entries)
                
                for theme, count in themes.items():
                    if count >= 3:  # Theme appears in at least 3 feedback entries
                        confidence = min(0.9, count / 10)  # Max confidence of 0.9
                        
                        insights.append(LearningInsight(
                            category="user_experience",
                            description=f"Common theme: {theme}",
                            confidence=confidence,
                            recommendations=self._generate_theme_recommendations(theme),
                            affected_components=self._identify_affected_components(theme),
                            priority=self._assess_theme_priority(theme, count)
                        ))
                
        except Exception as e:
            self.logger.error(f"Failed to analyze feedback content: {e}")
        
        return insights
    
    def _extract_themes(self, feedback_entries: List[Tuple]) -> Dict[str, int]:
        """Extract common themes from feedback content"""
        themes = {}
        
        # Simple keyword-based theme extraction
        theme_keywords = {
            "ui_issues": ["interface", "ui", "user interface", "confusing", "hard to use"],
            "performance": ["slow", "performance", "speed", "timeout", "lag"],
            "accuracy": ["wrong", "incorrect", "mistake", "error", "inaccurate"],
            "missing_features": ["missing", "need", "want", "should have", "lacking"],
            "documentation": ["docs", "documentation", "help", "unclear", "confusing"],
            "integration": ["integration", "compatibility", "conflict", "doesn't work with"]
        }
        
        for content, feedback_type, rating in feedback_entries:
            content_lower = content.lower()
            
            for theme, keywords in theme_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    themes[theme] = themes.get(theme, 0) + 1
        
        return themes
    
    def _generate_theme_recommendations(self, theme: str) -> List[str]:
        """Generate recommendations based on theme"""
        recommendations_map = {
            "ui_issues": [
                "Improve view generation templates",
                "Add UI/UX validation rules",
                "Create better default layouts"
            ],
            "performance": [
                "Optimize generated code",
                "Add performance monitoring",
                "Review database queries"
            ],
            "accuracy": [
                "Improve NLP parsing accuracy",
                "Add more validation checks",
                "Enhance training data"
            ],
            "missing_features": [
                "Expand feature detection",
                "Update requirement parsing",
                "Add new generation templates"
            ],
            "documentation": [
                "Improve generated documentation",
                "Add inline help text",
                "Create better user guides"
            ],
            "integration": [
                "Test with more Odoo versions",
                "Improve compatibility checks",
                "Add dependency validation"
            ]
        }
        
        return recommendations_map.get(theme, ["Review and improve based on feedback"])
    
    def _identify_affected_components(self, theme: str) -> List[str]:
        """Identify which components are affected by a theme"""
        component_map = {
            "ui_issues": ["code_generator", "config_engine"],
            "performance": ["code_generator", "integration"],
            "accuracy": ["nlp_parser"],
            "missing_features": ["nlp_parser", "config_engine"],
            "documentation": ["code_generator"],
            "integration": ["integration"]
        }
        
        return component_map.get(theme, ["general"])
    
    def _assess_theme_priority(self, theme: str, count: int) -> str:
        """Assess priority level for a theme"""
        priority_map = {
            "accuracy": "critical",
            "performance": "high",
            "integration": "high",
            "ui_issues": "medium",
            "missing_features": "medium",
            "documentation": "low"
        }
        
        base_priority = priority_map.get(theme, "medium")
        
        # Increase priority based on frequency
        if count >= 10:
            return "critical"
        elif count >= 7 and base_priority in ["medium", "low"]:
            return "high"
        elif count >= 5 and base_priority == "low":
            return "medium"
        
        return base_priority
    
    def _store_learning_insight(self, insight: LearningInsight) -> bool:
        """Store learning insight in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO learning_insights 
                    (category, description, confidence, recommendations, affected_components, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    insight.category,
                    insight.description,
                    insight.confidence,
                    json.dumps(insight.recommendations),
                    json.dumps(insight.affected_components),
                    insight.priority
                ))
                conn.commit()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store learning insight: {e}")
            return False
    
    def get_learning_insights(self, category: Optional[str] = None,
                            min_confidence: float = 0.5) -> List[LearningInsight]:
        """
        Get stored learning insights.
        
        Args:
            category: Optional category filter
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of learning insights
        """
        insights = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                where_clause = f"WHERE confidence >= {min_confidence}"
                params = []
                
                if category:
                    where_clause += " AND category = ?"
                    params.append(category)
                
                cursor = conn.execute(f"""
                    SELECT category, description, confidence, recommendations, 
                           affected_components, priority
                    FROM learning_insights 
                    {where_clause}
                    ORDER BY confidence DESC, timestamp DESC
                """, params)
                
                for row in cursor.fetchall():
                    insights.append(LearningInsight(
                        category=row[0],
                        description=row[1],
                        confidence=row[2],
                        recommendations=json.loads(row[3]),
                        affected_components=json.loads(row[4]),
                        priority=row[5]
                    ))
                
        except Exception as e:
            self.logger.error(f"Failed to get learning insights: {e}")
        
        return insights
    
    def export_feedback_data(self, format: str = "json") -> str:
        """
        Export feedback data for external analysis.
        
        Args:
            format: Export format ('json', 'csv')
            
        Returns:
            Serialized feedback data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT user_id, module_name, feedback_type, rating, content, 
                           metadata, timestamp
                    FROM feedback 
                    ORDER BY timestamp DESC
                """)
                
                feedback_data = []
                for row in cursor.fetchall():
                    feedback_data.append({
                        "user_id": row[0],
                        "module_name": row[1],
                        "feedback_type": row[2],
                        "rating": row[3],
                        "content": row[4],
                        "metadata": json.loads(row[5]) if row[5] else {},
                        "timestamp": row[6]
                    })
                
                if format == "json":
                    return json.dumps(feedback_data, indent=2, default=str)
                elif format == "csv":
                    import csv
                    import io
                    
                    output = io.StringIO()
                    if feedback_data:
                        writer = csv.DictWriter(output, fieldnames=feedback_data[0].keys())
                        writer.writeheader()
                        writer.writerows(feedback_data)
                    
                    return output.getvalue()
                else:
                    raise ValueError(f"Unsupported format: {format}")
                    
        except Exception as e:
            self.logger.error(f"Failed to export feedback data: {e}")
            return ""
    
    def cleanup_old_data(self, days: int = 365) -> bool:
        """
        Clean up old feedback data.
        
        Args:
            days: Number of days to keep data
            
        Returns:
            True if cleanup successful
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM feedback WHERE timestamp < ?", (cutoff_date,))
                conn.execute("DELETE FROM usage_metrics WHERE timestamp < ?", (cutoff_date,))
                conn.commit()
                
            self.logger.info(f"Cleaned up feedback data older than {days} days")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return False