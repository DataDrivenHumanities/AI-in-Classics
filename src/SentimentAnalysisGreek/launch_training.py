import sagemaker
import boto3
from sagemaker.huggingface import HuggingFace

try:
	role = sagemaker.get_execution_role()
except ValueError:
	iam = boto3.client('iam')
	role = iam.get_role(RoleName='SageMakerRole')['Role']['Arn']
		
hyperparameters = {
	'model_name_or_path':'pranaydeeps/Ancient-Greek-BERT',
	'output_dir':'/opt/ml/model',
    'epochs': 12,
    'per_device_train_batch_size': 64,
    'max_seq_length': 512,
    'learning_rate': 5e-5
}

# git configuration to download our fine-tuning script
git_config = {'repo': 'https://github.com/huggingface/transformers.git','branch': 'v4.49.0'}

# creates Hugging Face estimator
huggingface_estimator = HuggingFace(
	entry_point='run_glue.py',
	source_dir='./examples/pytorch/text-classification',
	instance_type='ml.p3.2xlarge',
	instance_count=1,
	role=role,
	git_config=git_config,
	transformers_version='4.49.0',
	pytorch_version='2.5.1',
	py_version='py311',
	hyperparameters = hyperparameters
)

# starting the train job
huggingface_estimator.fit(
    {'train': 's3://trojan-parse-greek/original_xml/train',
    'test': 's3://trojan-parse-greek/original_xml/test'}
)