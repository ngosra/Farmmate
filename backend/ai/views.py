from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.engine import ask
from ai.models import AssistantQuery
from api.access import require_membership
from organizations.models import Membership


class AssistantView(APIView):
    def get(self, request):
        member = require_membership(request)
        queryset = AssistantQuery.objects.filter(organization=member.organization)
        if member.role == Membership.Role.FARMER and not request.user.is_superuser:
            queryset = queryset.filter(user=request.user)
        return Response(
            [
                {
                    "id": str(row.id),
                    "question": row.question,
                    "answer": row.answer,
                    "intents": row.intents,
                    "created_at": row.created_at,
                }
                for row in queryset[:30]
            ]
        )

    def post(self, request):
        member = require_membership(request)
        question = str(request.data.get("question") or "").strip()
        if not question:
            raise ValidationError({"question": "Ask a question about your farm records."})
        if len(question) > 2000:
            raise ValidationError(
                {"question": "Ask a shorter question (2000 characters or fewer)."}
            )
        result = ask(request.user, member, question)
        AssistantQuery.objects.create(
            organization=member.organization,
            user=request.user,
            question=question,
            answer=result["answer"],
            intents=",".join(result["intents"]),
        )
        return Response(result)
