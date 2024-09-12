load('./tilt/cloudapi/Tiltfile', 'setup_cloudapi')
load('./tilt/metrics/Tiltfile', 'setup_metrics_server')
load('ext://color', 'color')
load('ext://helm_resource', 'helm_repo')

config.define_bool("no-build", False, "Skip building Docker images")
config.define_bool("destroy", False, "Destroy Kind cluster")
config.define_bool("destroy-all", False, "Destroy Kind cluster and delete docker cache")

update_settings(
  k8s_upsert_timeout_secs=600,
  max_parallel_updates=5,
)

# Restrict to `kind-aries-cloudapi` kube context
kind_cluster_name='kind-aries-cloudapi'
allow_k8s_contexts([kind_cluster_name])

if config.tilt_subcommand in ("up", "ci"):
  print(color.green('Setting up Istio'))
  local_resource(
    name='istio',
    cmd='mise run kind:install:istio',
    allow_parallel=True,
    labels=['99-networking']
  )

  print(color.green('Setting up Ingress Nginx'))
  local_resource(
    name='ingress-nginx',
    cmd='mise run kind:install:nginx',
    allow_parallel=True,
    labels=['99-networking']
  )

# Setup Metrics Server
setup_metrics_server()

# Validate `didx-xyz/charts` repo has been cloned
charts_dir='tilt/.charts'
if not os.path.exists(charts_dir):
  print(color.yellow('Charts not found, cloning charts repo'))

  ssh_result=str(local(
      'git clone git@github.com:didx-xyz/charts.git ' + charts_dir + ' 2>&1 | tee /dev/stdout',
      dir=os.path.dirname(__file__),
      quiet=True,
      echo_off=True)).strip()

  if 'fatal' in ssh_result:
    print(color.red('Failed to clone charts repo via SSH, retrying with HTTPS'))

    https_result=str(local(
        'git clone https://github.com/didx-xyz/charts.git ' + charts_dir + ' 2>&1 | tee /dev/stdout',
        dir=os.path.dirname(__file__),
        quiet=True,
        echo_off=True))

    if 'fatal' in https_result:
      fail(color.red('Failed to clone charts repo'))

  print(color.green('Charts repo cloned'))
else:
  print(color.green('Charts repo already cloned'))

# Setup CloudAPI
build_enabled = not config.parse().get("no-build")
setup_cloudapi(build_enabled)

if config.tilt_subcommand not in ("down"):
  # _FORCE_ Kube Context to `kind-aries-cloudapi`
  local('kubectl config use-context ' + kind_cluster_name, dir=os.path.dirname(__file__))

if config.tilt_subcommand in ("down"):
  destroy = config.parse().get("destroy")
  destroy_all = config.parse().get("destroy-all")

  if destroy_all:
    print(color.red('Destroying Kind cluster and deleting docker cache'))
    local('docker compose -f ./docker-compose-ledger.yaml down -v', dir=os.path.dirname(__file__))
    local('mise run kind:destroy:all', dir=os.path.dirname(__file__))

  if destroy:
    print(color.red('Destroying Kind cluster'))
    local('docker compose -f ./docker-compose-ledger.yaml down -v', dir=os.path.dirname(__file__))
    local('mise run kind:destroy', dir=os.path.dirname(__file__))
