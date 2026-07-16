import pytest
from pydantic import ValidationError
from hermes_video.editorial_model import DeterministicEditorialModel, ModelBudget, SemanticResult, SemanticUnit

def test_model_schema_and_deterministic_mock():
    result=DeterministicEditorialModel().analyze([{"id":"u","text":"A useful complete explanation"}],ModelBudget())
    assert isinstance(result,SemanticResult) and result.units[0].unit_id=="u"
    with pytest.raises(ValidationError): SemanticUnit(unit_id="x",summary="x",quality=2)

def test_token_budget_fails_honestly():
    with pytest.raises(RuntimeError,match="budget"):
        DeterministicEditorialModel().analyze([{"id":"u","text":"too many words"}],ModelBudget(max_tokens=1))
