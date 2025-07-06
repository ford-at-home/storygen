"""CI/CD Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    Duration,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as pipeline_actions,
    aws_codebuild as codebuild,
    aws_codedeploy as codedeploy,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_s3 as s3,
    CfnOutput,
)
from constructs import Construct


class CICDStack(Stack):
    """Creates CodePipeline for automated deployments"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR Repository
        self.ecr_repo = ecr.Repository(
            self,
            "ECRRepository",
            repository_name="storygen",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10,
                    rule_priority=1,
                ),
                ecr.LifecycleRule(
                    description="Remove untagged images after 1 day",
                    max_image_age=Duration.days(1),
                    tag_status=ecr.TagStatus.UNTAGGED,
                    rule_priority=2,
                ),
            ],
        )

        # S3 Bucket for artifacts
        artifacts_bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name=f"storygen-artifacts-{env_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldArtifacts",
                    expiration=Duration.days(30),
                    noncurrent_version_expiration=Duration.days(7),
                ),
            ],
        )

        # CodeBuild role
        build_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryPowerUser"),
            ],
        )

        # Build project for testing
        test_project = codebuild.PipelineProject(
            self,
            "TestProject",
            project_name=f"storygen-test-{env_name}",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                environment_variables={
                    "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                    "AWS_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                },
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo Installing dependencies...",
                            "pip install -r requirements-lock.txt",
                            "pip install pytest pytest-cov black flake8 mypy bandit safety",
                            "cd frontend && npm ci && cd ..",
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Running Python tests...",
                            "black --check .",
                            "flake8 .",
                            "mypy .",
                            "bandit -r . -f json -o bandit-report.json",
                            "safety check --json",
                            "pytest tests/ --cov=. --cov-report=xml",
                            "echo Running frontend tests...",
                            "cd frontend && npm run lint && npm run type-check && npm run test:ci && cd ..",
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Tests completed successfully!",
                        ]
                    }
                },
                "reports": {
                    "pytest_reports": {
                        "files": ["**/*"],
                        "base-directory": "pytest-reports",
                        "file-format": "JUNITXML",
                    },
                    "coverage_reports": {
                        "files": ["coverage.xml"],
                        "file-format": "COBERTURAXML",
                    }
                },
                "artifacts": {
                    "files": [
                        "bandit-report.json",
                        "coverage.xml",
                    ]
                }
            }),
            role=build_role,
        )

        # Build project for Docker image
        build_project = codebuild.PipelineProject(
            self,
            "BuildProject",
            project_name=f"storygen-build-{env_name}",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.LARGE,
                privileged=True,
                environment_variables={
                    "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                    "AWS_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                    "ECR_REPO_URI": codebuild.BuildEnvironmentVariable(value=self.ecr_repo.repository_uri),
                },
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo Logging in to Amazon ECR...",
                            "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URI",
                            "COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)",
                            "IMAGE_TAG=${COMMIT_HASH:=latest}",
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Building Docker image...",
                            "docker build -t $ECR_REPO_URI:latest .",
                            "docker tag $ECR_REPO_URI:latest $ECR_REPO_URI:$IMAGE_TAG",
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Pushing Docker image...",
                            "docker push $ECR_REPO_URI:latest",
                            "docker push $ECR_REPO_URI:$IMAGE_TAG",
                            "echo Writing image definitions file...",
                            'printf \'[{"name":"app","imageUri":"%s"}]\' $ECR_REPO_URI:$IMAGE_TAG > imagedefinitions.json',
                        ]
                    }
                },
                "artifacts": {
                    "files": ["imagedefinitions.json"]
                }
            }),
            role=build_role,
        )

        # Grant ECR permissions
        self.ecr_repo.grant_pull_push(build_role)

        # CodeDeploy application
        deploy_app = codedeploy.EcsApplication(
            self,
            "DeployApplication",
            application_name=f"storygen-{env_name}",
        )

        # Deployment group
        deploy_group = codedeploy.EcsDeploymentGroup(
            self,
            "DeploymentGroup",
            application=deploy_app,
            deployment_group_name=f"storygen-{env_name}-dg",
            deployment_config=codedeploy.EcsDeploymentConfig.ALL_AT_ONCE_BLUE_GREEN,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                blue_target_group=elbv2.ApplicationTargetGroup.from_target_group_attributes(
                    self, "BlueTargetGroup",
                    target_group_arn=f"arn:aws:elasticloadbalancing:{self.region}:{self.account}:targetgroup/storygen-{env_name}-blue/*"
                ),
                green_target_group=elbv2.ApplicationTargetGroup.from_target_group_attributes(
                    self, "GreenTargetGroup",
                    target_group_arn=f"arn:aws:elasticloadbalancing:{self.region}:{self.account}:targetgroup/storygen-{env_name}-green/*"
                ),
                listener=elbv2.ApplicationListener.from_lookup(
                    self, "ProdListener",
                    listener_arn=f"arn:aws:elasticloadbalancing:{self.region}:{self.account}:listener/app/storygen-{env_name}/*"
                ),
                deployment_approval_wait_time=Duration.minutes(5),
                termination_wait_time=Duration.minutes(5),
            ),
            auto_rollback=codedeploy.AutoRollbackConfig(
                deployment_in_alarm=True,
                failed_deployment=True,
                stopped_deployment=True,
            ),
        )

        # Pipeline
        pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            pipeline_name=f"storygen-{env_name}",
            artifact_bucket=artifacts_bucket,
            restart_execution_on_update=True,
        )

        # Source stage
        source_output = codepipeline.Artifact("SourceOutput")
        source_action = pipeline_actions.GitHubSourceAction(
            action_name="GitHub_Source",
            owner="your-github-org",
            repo="storygen",
            branch="main" if env_name == "prod" else "develop",
            oauth_token=cdk.SecretValue.secrets_manager("github-token"),
            output=source_output,
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action],
        )

        # Test stage
        test_output = codepipeline.Artifact("TestOutput")
        test_action = pipeline_actions.CodeBuildAction(
            action_name="Test",
            project=test_project,
            input=source_output,
            outputs=[test_output],
        )

        pipeline.add_stage(
            stage_name="Test",
            actions=[test_action],
        )

        # Build stage
        build_output = codepipeline.Artifact("BuildOutput")
        build_action = pipeline_actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output],
        )

        pipeline.add_stage(
            stage_name="Build",
            actions=[build_action],
        )

        # Deploy stage
        deploy_action = pipeline_actions.EcsDeployAction(
            action_name="Deploy",
            service=ecs.FargateService.from_fargate_service_attributes(
                self, "Service",
                service_arn=f"arn:aws:ecs:{self.region}:{self.account}:service/storygen-{env_name}/storygen-{env_name}"
            ),
            input=build_output,
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[deploy_action],
        )

        # Manual approval for production
        if env_name == "prod":
            approval_action = pipeline_actions.ManualApprovalAction(
                action_name="ApproveProduction",
                notification_topic=sns.Topic.from_topic_arn(
                    self, "ApprovalTopic",
                    f"arn:aws:sns:{self.region}:{self.account}:storygen-approvals"
                ),
                additional_information="Please review the changes and approve for production deployment",
            )

            pipeline.add_stage(
                stage_name="Approval",
                actions=[approval_action],
                placement=codepipeline.StagePlacement(
                    just_after=pipeline.stage("Test")
                ),
            )

        # Outputs
        CfnOutput(
            self,
            "ECRRepositoryURI",
            value=self.ecr_repo.repository_uri,
            export_name=f"{env_name}-ecr-repo-uri",
        )

        CfnOutput(
            self,
            "PipelineName",
            value=pipeline.pipeline_name,
            export_name=f"{env_name}-pipeline-name",
        )

        CfnOutput(
            self,
            "PipelineArn",
            value=pipeline.pipeline_arn,
            export_name=f"{env_name}-pipeline-arn",
        )