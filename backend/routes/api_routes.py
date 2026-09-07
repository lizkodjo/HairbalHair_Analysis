from flask import Blueprint, jsonify, request
from config import Config

bp = Blueprint("api", __name__)

# Service instances
_recommendation_service = None
_herb_repo = None
_classifier_service = None
_ai_service = None


def init_services(recommendation_service, herb_repo, classifier_service, ai_service):
    """Initialise services for routes"""
    global _recommendation_service, _herb_repo, _classifier_service, _ai_service
    _recommendation_service = recommendation_service
    _herb_repo = herb_repo
    _classifier_service = classifier_service
    _ai_service = ai_service


def _get_services():
    """Get services (with error if not initialised)"""
    if _recommendation_service is None:
        raise RuntimeError("Services not initialised")
    return _recommendation_service, _herb_repo, _classifier_service, _ai_service


# Condition Icons mapping
CONDITION_ICONS = {
    "Hair Growth": "🌱",
    "Hair Fall": "💧",
    "Dandruff": "🧴",
    "Dry Hair": "🏜️",
    "Oily Scalp": "💦",
    "Itchy Scalp": "🤕",
    "Split Ends": "✂️",
    "Premature Greying": "🕊️",
    "Thinning Hair": "📉",
    "Frizz": "🌀",
    "Scalp Health": "🧖",
    "Scalp Infections": "🦠",
    "Dull Hair": "😐",
    "Stress Hair Loss": "😰",
    "Hair Shine": "✨",
    "Hair Strength": "💪",
}


# Health endpoints
@bp.route("/health", methods=["GET"])
def health_check():
    """Health check"""
    _, herb_repo, classifier, ai = _get_services()

    return jsonify(
        {
            "status": "healthy",
            "mode": "condition-first-with-optional-image",
            "components": {
                "herb_database": {
                    "loaded": herb_repo.count() > 0,
                    "count": herb_repo.count(),
                    "hair_growth_focused": True,
                },
                "hair_classifier": {
                    "available": classifier.available,
                    "types": classifier.HAIR_TYPES if classifier.available else [],
                },
                "llm_api": {
                    "available": ai.available,
                    "model": ai.model_name or "Not configured",
                    "batch_mode": True,
                },
            },
            "features": {
                "condition_based_recommendations": True,
                "image_classification": classifier.available,
                "ai_explanations": ai.available,
                "optional_upload": True,
                "batch_processing": True,
            },
        }
    )


# Condition endpoints
@bp.route("/conditions", methods=["GET"])
def get_available_condtions():
    """Get all available hair conditions with icons"""
    _, herb_repo, _, _ = _get_services()

    conditions = []
    for condition in herb_repo.get_all_conditions():
        icon = CONDITION_ICONS.get(condition, "🌿")
        conditions.append(
            {
                "id": condition.lower().replace(" ", "_"),
                "name": condition,
                "icon": icon,
                "description": f"Addresses {condition.lower()}",
            }
        )

    return jsonify(
        {"success": True, "count": len(conditions), "conditions": conditions}
    )


@bp.route("/hair-types", methods=["GET"])
def get_hair_types():
    """Get all available hair types"""
    _, herb_repo, _, _ = _get_services()

    return jsonify({"success": True, "hair_types": herb_repo.get_all_hair_types()})


# ----- Herb Endpoints -----


@bp.route("/herbs", methods=["GET"])
def get_all_herbs():
    """Get all herbs in the database"""
    _, herb_repo, _, _ = _get_services()

    try:
        herbs = herb_repo.get_all()
        return jsonify({"success": True, "count": len(herbs), "herbs": herbs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/herbs/search", methods=["GET"])
def search_herbs():
    """Search herbs by name, benefits, conditions or botanical name"""
    _, herb_repo, _, _ = _get_services()

    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Please provide a search query"}), 400

    try:
        results = herb_repo.search(query)
        return jsonify(
            {"success": True, "query": query, "count": len(results), "results": results}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/herbs/condition/<condition>", methods=["GET"])
def get_herbs_by_condition(condition):
    """Get herbs for a specific condition"""
    _, herb_repo, _, _ = _get_services()

    try:
        results = herb_repo.get_by_condition(condition)
        return jsonify(
            {
                "success": True,
                "condition": condition,
                "count": len(results),
                "herbs": results,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/herbs/hair-type/<hair_type>", methods=["GET"])
def get_herbs_by_hair_type(hair_type):
    """Get herbs suitable for a specific hair type"""
    _, herb_repo, _, _ = _get_services()

    try:
        results = herb_repo.get_by_hair_type(hair_type)
        return jsonify(
            {
                "success": True,
                "hair_type": hair_type,
                "count": len(results),
                "herbs": results,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/herbs/top", methods=["GET"])
def get_top_herbs():
    """Get top herbs based on match score"""
    _, herb_repo, _, _ = _get_services()

    limit = request.args.get("limit", 10, type=int)

    try:
        if "match_score" in herb_repo.df.columns:
            top_herbs = herb_repo.df.nlargest(limit, "match_score")
        else:
            top_herbs = herb_repo.df.head(limit)

        return jsonify(
            {
                "success": True,
                "count": len(top_herbs),
                "herbs": top_herbs.to_dict("records"),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ----- Recommendation Endpoints -----


@bp.route("/recommend", methods=["POST"])
def get_recommendations():
    """Get herb recommendations based on selected conditions only"""
    rec_service, _, _, _ = _get_services()

    try:
        data = request.get_json()

        if not data or "conditions" not in data:
            return (
                jsonify(
                    {"success": False, "error": "Please select at least one condition"}
                ),
                400,
            )

        conditions = data["conditions"]
        if not isinstance(conditions, list) or len(conditions) == 0:
            return (
                jsonify(
                    {"success": False, "error": "Please select at least one condition"}
                ),
                400,
            )

        limit = data.get("limit", Config.DEFAULT_LIMIT)
        include_ai = data.get("include_ai", True)

        result = rec_service.recommend_by_conditions(conditions, limit, include_ai)

        if not result.get("success"):
            return jsonify(result), 404

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/predict", methods=["POST"])
def predict_with_image():
    """OPTIONAL: Get recommendations with image-based hair type prediction"""
    rec_service, _, _, _ = _get_services()

    try:
        # Check if image was uploaded
        has_image = "image" in request.files and request.files["image"].filename != ""

        # Get conditions from form data
        conditions_str = request.form.get("conditions", "")
        conditions = [c.strip() for c in conditions_str.split(",") if c.strip()]

        if not conditions:
            return (
                jsonify(
                    {"success": False, "error": "Please select at least one condition"}
                ),
                400,
            )

        # Read image data if provided
        image_data = None
        if has_image:
            image_data = request.files["image"].read()

        result = rec_service.recommend_with_image(conditions, image_data)

        if not result.get("success"):
            return jsonify(result), 404

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ----- Stats Endpoint -----


@bp.route("/data/stats", methods=["GET"])
def get_data_statistics():
    """Get comprehensive statistics about the herb database"""
    _, herb_repo, _, _ = _get_services()

    try:
        stats = herb_repo.get_stats()
        return jsonify({"success": True, "statistics": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
