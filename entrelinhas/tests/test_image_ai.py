import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import image_ai
import review_store


COMPLETE='Gráfico de consumo de água, em litros. Segunda: 320; terça: 280; quarta: 360.'
SUGGESTION=('Gráfico de barras mostrando o consumo de água em litros na Segunda-feira (320L), '
    'Terça-feira (280L) e Quarta-feira (360L).')


def assessment():
    return {
        'matches_image':True,'sufficient':True,'image_summary':'Consumo de água em três dias, em litros.',
        'image_type':'chart',
        'essential_details':[{'fact':'Consumo de água','evidence':'consumo de água'}],
        'data_points':[
            {'label':'Segunda','value':'320','unit':'litros','evidence':'Segunda: 320'},
            {'label':'Terça','value':'280','unit':'litros','evidence':'terça: 280'},
            {'label':'Quarta','value':'360','unit':'litros','evidence':'quarta: 360'},
        ],
        'score':1000,'verdict':'adequada','explanation':'A descrição está boa.',
        'differences':[],'suggested_description':'','visible_text':'Segunda 320; Terça 280; Quarta 360; Litros',
    }


class DescriptionAssessmentTests(unittest.TestCase):
    def check_result(self,description,result=None):
        result=image_ai.validate_result(result or assessment())
        return image_ai.public_result(image_ai.normalize_result(result,description))

    def test_topic_only_is_not_approved_even_when_model_gives_one_thousand(self):
        result=self.check_result('Gráfico de consumo de água')
        self.assertFalse(result['approved'])
        self.assertEqual(result['verdict'],'parcial')
        self.assertTrue(any('320' in item for item in result['differences']))
        self.assertTrue(any('280' in item for item in result['differences']))

    def test_screenshot_suggestion_with_attached_units_is_accepted(self):
        result=assessment()
        for point in result['data_points']:
            point['evidence']=point['label']+'-feira ('+point['value']+'L)'
        self.assertTrue(self.check_result(SUGGESTION,result)['approved'])

    def test_present_data_are_not_lost_when_the_model_omits_evidence(self):
        result=assessment()
        for point in result['data_points']:point['evidence']=''
        self.assertTrue(self.check_result(SUGGESTION,result)['approved'])

    def test_decimal_values_with_attached_units_are_not_lost(self):
        result=assessment()
        values=['320,5','280,25','360,75']
        for point,value in zip(result['data_points'],values):
            point.update(value=value,evidence='')
        description='Consumo de água: Segunda: 320,5L; terça: 280,25L; quarta: 360,75L.'
        self.assertTrue(self.check_result(description,result)['approved'])

    def test_numeric_sign_is_not_discarded_by_format_normalization(self):
        result=assessment()
        result['data_points'][0].update(value='-320',evidence='Segunda: -320L')
        self.assertFalse(self.check_result(COMPLETE,result)['approved'])

    def test_threshold_is_strictly_above_950_and_score_stays_internal(self):
        for score,approved in ((950,False),(951,True),(1000,True)):
            with self.subTest(score=score):
                result=assessment();result['score']=score
                checked=self.check_result(COMPLETE,result)
                self.assertEqual(checked['approved'],approved)
                self.assertNotIn('score',checked)
        result=assessment();result['score']=1001
        with self.assertRaises(image_ai.ImageAIError):image_ai.validate_result(result)

    def test_complete_data_are_approved_without_exposing_internal_assessment(self):
        result=self.check_result(COMPLETE)
        self.assertTrue(result['approved'])
        self.assertEqual(result['suggested_description'],'')
        for name in ('score','image_type','essential_details','data_points'):
            self.assertNotIn(name,result)

    def test_matching_but_incomplete_description_is_partial_not_incompatible(self):
        result=assessment()
        result.update(score=400,sufficient=False,verdict='incompativel',differences=['Faltam os dados.'])
        checked=self.check_result('Gráfico de consumo de água',result)
        self.assertFalse(checked['approved'])
        self.assertEqual(checked['verdict'],'parcial')

    def test_missing_category_value_or_unit_prevents_approval(self):
        for description in (
            COMPLETE.replace('; quarta: 360',''),
            COMPLETE.replace('terça: 280','terça'),
            COMPLETE.replace(', em litros',''),
            COMPLETE.replace('litros','mililitros'),
        ):
            with self.subTest(description=description):
                self.assertFalse(self.check_result(description)['approved'])

    def test_reassigned_values_do_not_pass_even_if_both_numbers_are_present(self):
        result=assessment()
        result['data_points'][0]['evidence']='Segunda: 280'
        result['data_points'][1]['evidence']='terça: 320'
        self.assertFalse(self.check_result(COMPLETE.replace('Segunda: 320; terça: 280',
            'Segunda: 280; terça: 320'),result)['approved'])

    def test_whole_paragraph_evidence_does_not_hide_correct_data(self):
        result=assessment()
        for point in result['data_points']:point['evidence']=COMPLETE
        self.assertTrue(self.check_result(COMPLETE,result)['approved'])

    def test_whole_paragraph_evidence_does_not_approve_reassigned_values(self):
        result=assessment()
        swapped=COMPLETE.replace('Segunda: 320; terça: 280','Segunda: 280; terça: 320')
        for point in result['data_points']:point['evidence']=swapped
        self.assertFalse(self.check_result(swapped,result)['approved'])

    def test_portuguese_numbers_and_usual_unit_abbreviation_are_accepted(self):
        result=assessment()
        expressions=['trezentos e vinte','duzentos e oitenta','trezentos e sessenta']
        for point,expression in zip(result['data_points'],expressions):
            point['evidence']=point['label']+': '+expression
        description='Gráfico de consumo de água, em L. '+ '; '.join(p['evidence'] for p in result['data_points'])+'.'
        self.assertTrue(self.check_result(description,result)['approved'])

    def test_unreadable_chart_cannot_be_approved(self):
        result=assessment();result['data_points']=[]
        self.assertFalse(self.check_result(COMPLETE,result)['approved'])

    def test_non_quantitative_image_does_not_require_numeric_data(self):
        result=assessment()
        result.update(image_type='photo',image_summary='Uma flor amarela com folhas verdes.',data_points=[],
            essential_details=[{'fact':'Flor amarela com folhas verdes','evidence':'flor amarela com folhas verdes'}])
        self.assertTrue(self.check_result('Uma flor amarela com folhas verdes.',result)['approved'])

    def test_missing_fact_in_non_quantitative_image_prevents_approval(self):
        result=assessment()
        result.update(image_type='diagram',data_points=[],
            essential_details=[{'fact':'A seta indica a evaporação','evidence':''}])
        self.assertFalse(self.check_result('Diagrama do ciclo da água.',result)['approved'])

    def test_malformed_extraction_is_rejected(self):
        result=assessment();result['data_points'][0]['evidence']=True
        with self.assertRaises(image_ai.ImageAIError):image_ai.validate_result(result)


class ApprovalCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        data=BytesIO();Image.new('RGB',(4,4),'white').save(data,format='PNG')
        self.image='data:image/png;base64,'+base64.b64encode(data.getvalue()).decode('ascii')
        self.addCleanup(image_ai._cache.clear)
        image_ai._cache.clear()

    def response(self):
        response=unittest.mock.MagicMock()
        response.__enter__.return_value=response
        response.read.return_value=json.dumps({'choices':[{'finish_reason':'stop',
            'message':{'content':json.dumps(assessment())}}]}).encode()
        return response

    def verify(self,description):
        return image_ai.verify(self.image,description,'regression',self.folder/'ai_checks.json','image',self.folder)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_partial_results_do_not_consume_approvals_or_repeated_network_calls(self):
        with patch('image_ai.urllib.request.urlopen',return_value=self.response()) as network:
            for _ in range(3):
                result=self.verify('Gráfico de consumo de água')
                self.assertFalse(result['approved'])
                self.assertEqual(result['checks_remaining'],2)
            self.assertEqual(network.call_count,2)
        status=review_store.ai_status(self.folder,image_ai.approval_key(self.image,'Gráfico de consumo de água'))
        self.assertEqual(status['accepted_count'],0)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_two_approvals_reuse_one_call_and_then_block_only_that_text(self):
        with patch('image_ai.urllib.request.urlopen',return_value=self.response()) as network:
            self.assertTrue(self.verify(COMPLETE)['approved'])
            second=self.verify(COMPLETE)
            self.assertTrue(second['cached'])
            self.assertEqual(second['checks_used'],2)
            with self.assertRaisesRegex(image_ai.ImageAIError,'duas vezes'):self.verify(COMPLETE)
            self.assertEqual(network.call_count,1)
            self.assertFalse(self.verify('Gráfico de consumo de água')['approved'])
            self.assertEqual(network.call_count,3)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_old_approvals_do_not_reappear_or_block_a_new_evaluation(self):
        old_key='v3:'+image_ai.approval_key(self.image,COMPLETE).split(':',1)[1]
        review_store.accept_ai(self.folder,old_key,assessment())
        review_store.accept_ai(self.folder,old_key,assessment())
        (self.folder/'ai_checks.json').write_text(json.dumps({'image':{
            'approval_key':old_key,'description':COMPLETE,'result':assessment()}}),encoding='utf-8')
        old=image_ai.usage_status(self.folder/'ai_checks.json',self.folder)['image']
        self.assertEqual(old['used'],0)
        self.assertIsNone(old['result'])
        with patch('image_ai.urllib.request.urlopen',return_value=self.response()) as network:
            self.assertTrue(self.verify(COMPLETE)['approved'])
            self.assertEqual(network.call_count,1)

    def partial_with_suggestion(self):
        result=assessment()
        result.update(score=600,sufficient=False,verdict='parcial',explanation='Faltam os dias e os valores.',
            differences=['Faltam os dados do gráfico.'],suggested_description=SUGGESTION)
        return result

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_offered_suggestion_is_verified_and_reused_even_after_restart(self):
        with patch('image_ai.request_assessment',side_effect=[self.partial_with_suggestion(),assessment()]) as request:
            original=self.verify('Gráfico de consumo de água')
            self.assertFalse(original['approved'])
            self.assertEqual(original['suggested_description'],SUGGESTION)
            state=review_store.ai_status(self.folder,image_ai.approval_key(self.image,SUGGESTION))
            self.assertEqual(state['accepted_count'],0)
            self.assertGreater(state['result']['score'],950)
            first=self.verify(SUGGESTION)
            self.assertTrue(first['approved'])
            self.assertTrue(first['cached'])
            self.assertEqual(first['suggested_description'],'')
            image_ai._cache.clear()
            second=self.verify(SUGGESTION)
            self.assertTrue(second['approved'])
            self.assertEqual(second['checks_used'],2)
            with self.assertRaisesRegex(image_ai.ImageAIError,'duas vezes'):self.verify(SUGGESTION)
            self.assertEqual(request.call_count,2)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_unapproved_suggestion_is_not_offered_or_followed_by_another_suggestion(self):
        followup=self.partial_with_suggestion();followup['suggested_description']='Outra sugestão.'
        with patch('image_ai.request_assessment',side_effect=[self.partial_with_suggestion(),followup]) as request:
            result=self.verify('Gráfico de consumo de água')
            self.assertFalse(result['approved'])
            self.assertEqual(result['suggested_description'],'')
            self.assertEqual(request.call_count,2)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_overrated_original_can_offer_only_a_verified_candidate_from_image_data(self):
        overrated=image_ai.normalize_result(assessment(),'Gráfico de consumo de água')
        with patch('image_ai.request_assessment',side_effect=[overrated,assessment()]) as request:
            result=self.verify('Gráfico de consumo de água')
            self.assertFalse(result['approved'])
            self.assertIn('Segunda: 320 litros',result['suggested_description'])
            self.assertEqual(request.call_count,2)
            self.assertTrue(self.verify(result['suggested_description'])['approved'])
            self.assertEqual(request.call_count,2)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_complete_visual_summary_is_not_followed_by_duplicate_data(self):
        original=assessment();original['image_summary']=COMPLETE
        overrated=image_ai.normalize_result(original,'Gráfico de consumo de água')
        with patch('image_ai.request_assessment',side_effect=[overrated,assessment()]):
            result=self.verify('Gráfico de consumo de água')
            self.assertEqual(result['suggested_description'],COMPLETE)

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_failure_to_verify_suggestion_preserves_the_original_feedback(self):
        with patch('image_ai.request_assessment',side_effect=[self.partial_with_suggestion(),image_ai.ImageAIError('Indisponível')]):
            result=self.verify('Gráfico de consumo de água')
            self.assertFalse(result['approved'])
            self.assertEqual(result['suggested_description'],'')
            self.assertEqual(result['explanation'],'Faltam os dias e os valores.')

    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'})
    def test_suggestion_cache_does_not_reset_existing_approval_limits(self):
        identity=image_ai.approval_key(self.image,SUGGESTION)
        review_store.accept_ai(self.folder,identity,assessment())
        review_store.accept_ai(self.folder,identity,assessment())
        with patch('image_ai.request_assessment',return_value=self.partial_with_suggestion()) as request:
            result=self.verify('Gráfico de consumo de água')
            self.assertEqual(result['suggested_description'],SUGGESTION)
            self.assertEqual(request.call_count,1)
        self.assertEqual(review_store.ai_status(self.folder,identity)['accepted_count'],2)


if __name__=='__main__':unittest.main()
