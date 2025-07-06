"""CDN Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    CfnOutput,
)
from constructs import Construct


class CDNStack(Stack):
    """Creates CloudFront distribution for global content delivery"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        alb: elbv2.ApplicationLoadBalancer,
        s3_bucket: s3.Bucket,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Origin Access Identity for S3
        oai = cloudfront.OriginAccessIdentity(
            self,
            "OAI",
            comment=f"OAI for StoryGen {env_name}",
        )

        # Grant read permissions to OAI
        s3_bucket.grant_read(oai)

        # Response headers policy for security
        response_headers_policy = cloudfront.ResponseHeadersPolicy(
            self,
            "ResponseHeadersPolicy",
            response_headers_policy_name=f"storygen-{env_name}-headers",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                    override=True,
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True,
                ),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(365),
                    include_subdomains=True,
                    preload=True,
                    override=True,
                ),
                xss_protection=cloudfront.ResponseHeadersXSSProtection(
                    protection=True,
                    mode_block=True,
                    override=True,
                ),
            ),
            custom_headers_behavior=cloudfront.ResponseCustomHeadersBehavior(
                custom_headers=[
                    cloudfront.ResponseCustomHeader(
                        header="Cache-Control",
                        value="public, max-age=31536000, immutable",
                        override=False,
                    ),
                ]
            ),
        )

        # Cache policies
        api_cache_policy = cloudfront.CachePolicy(
            self,
            "APICachePolicy",
            cache_policy_name=f"storygen-{env_name}-api-cache",
            default_ttl=Duration.seconds(0),
            max_ttl=Duration.seconds(1),
            min_ttl=Duration.seconds(0),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            header_behavior=cloudfront.CacheHeaderBehavior.allow_list(
                "Authorization",
                "Content-Type",
                "X-Requested-With",
            ),
        )

        static_cache_policy = cloudfront.CachePolicy(
            self,
            "StaticCachePolicy",
            cache_policy_name=f"storygen-{env_name}-static-cache",
            default_ttl=Duration.days(1),
            max_ttl=Duration.days(365),
            min_ttl=Duration.days(1),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )

        # Origin request policy for API
        api_origin_policy = cloudfront.OriginRequestPolicy(
            self,
            "APIOriginPolicy",
            origin_request_policy_name=f"storygen-{env_name}-api-origin",
            query_string_behavior=cloudfront.OriginRequestQueryStringBehavior.all(),
            header_behavior=cloudfront.OriginRequestHeaderBehavior.allow_list(
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "User-Agent",
                "Referer",
            ),
            cookie_behavior=cloudfront.OriginRequestCookieBehavior.all(),
        )

        # CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            domain_names=[f"storygen.{env_name}.example.com"] if env_name != "prod" else ["storygen.example.com", "www.storygen.example.com"],
            certificate=acm.Certificate.from_certificate_arn(
                self,
                "Certificate",
                f"arn:aws:acm:us-east-1:{self.account}:certificate/your-cert-id",
            ),
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL if env_name == "prod" else cloudfront.PriceClass.PRICE_CLASS_100,
            enable_logging=True,
            log_bucket=s3.Bucket.from_bucket_name(
                self,
                "LogsBucket",
                f"storygen-logs-{env_name}-{self.account}",
            ),
            log_file_prefix=f"cloudfront/{env_name}/",
            geo_restriction=cloudfront.GeoRestriction.allowlist("US", "CA", "GB", "AU"),
            web_acl_id=f"arn:aws:wafv2:{self.region}:{self.account}:regional/webacl/{env_name}-waf/*" if env_name == "prod" else None,
            comment=f"StoryGen {env_name} CloudFront Distribution",
            
            # Default behavior for API
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    alb.load_balancer_dns_name,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    origin_path="/api",
                    custom_headers={
                        "X-Custom-Header": "CloudFront",
                    },
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=api_cache_policy,
                origin_request_policy=api_origin_policy,
                response_headers_policy=response_headers_policy,
                compress=True,
            ),
            
            # Additional behaviors
            additional_behaviors={
                # Static assets from S3
                "/static/*": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(
                        s3_bucket,
                        origin_access_identity=oai,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=static_cache_policy,
                    response_headers_policy=response_headers_policy,
                    compress=True,
                ),
                # Health check endpoint (no caching)
                "/health": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        alb.load_balancer_dns_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                ),
                # WebSocket support
                "/ws/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        alb.load_balancer_dns_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=api_origin_policy,
                ),
            },
            
            # Error pages
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200,
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_page_path="/error.html",
                    response_http_status=403,
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=500,
                    ttl=Duration.seconds(10),
                ),
                cloudfront.ErrorResponse(
                    http_status=502,
                    ttl=Duration.seconds(10),
                ),
                cloudfront.ErrorResponse(
                    http_status=503,
                    ttl=Duration.seconds(10),
                ),
                cloudfront.ErrorResponse(
                    http_status=504,
                    ttl=Duration.seconds(10),
                ),
            ],
        )

        # Route53 alias record (if using custom domain)
        if env_name == "prod":
            hosted_zone = route53.HostedZone.from_lookup(
                self,
                "HostedZone",
                domain_name="example.com",
            )

            route53.ARecord(
                self,
                "AliasRecord",
                zone=hosted_zone,
                record_name="storygen",
                target=route53.RecordTarget.from_alias(
                    targets.CloudFrontTarget(self.distribution)
                ),
            )

            route53.ARecord(
                self,
                "WwwAliasRecord",
                zone=hosted_zone,
                record_name="www.storygen",
                target=route53.RecordTarget.from_alias(
                    targets.CloudFrontTarget(self.distribution)
                ),
            )

        # Outputs
        CfnOutput(
            self,
            "DistributionId",
            value=self.distribution.distribution_id,
            export_name=f"{env_name}-distribution-id",
        )

        CfnOutput(
            self,
            "DistributionDomainName",
            value=self.distribution.distribution_domain_name,
            export_name=f"{env_name}-distribution-domain",
        )

        CfnOutput(
            self,
            "DistributionURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            export_name=f"{env_name}-distribution-url",
        )