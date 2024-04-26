import { useActions, useValues } from 'kea'
import { NotFound } from 'lib/components/NotFound'
import { LemonButton } from 'lib/lemon-ui/LemonButton'
import { LemonMarkdown } from 'lib/lemon-ui/LemonMarkdown'
import { LemonTable } from 'lib/lemon-ui/LemonTable'
import { SceneExport } from 'scenes/sceneTypes'

import { BatchExportService, PipelineStage, PluginType } from '~/types'

import { pipelineDestinationsLogic } from './destinationsLogic'
import { frontendAppsLogic } from './frontendAppsLogic'
import { PipelineBatchExportConfiguration } from './PipelineBatchExportConfiguration'
import { PIPELINE_TAB_TO_NODE_STAGE } from './PipelineNode'
import { pipelineNodeNewLogic, PipelineNodeNewLogicProps } from './pipelineNodeNewLogic'
import { PipelinePluginConfiguration } from './PipelinePluginConfiguration'
import { pipelineTransformationsLogic } from './transformationsLogic'
import { RenderApp, RenderBatchExportIcon } from './utils'

const paramsToProps = ({
    params: { stage, pluginIdOrBatchExportDestination },
}: {
    params: { stage?: string; pluginIdOrBatchExportDestination?: string }
}): PipelineNodeNewLogicProps => {
    const numericId =
        pluginIdOrBatchExportDestination && /^\d+$/.test(pluginIdOrBatchExportDestination)
            ? parseInt(pluginIdOrBatchExportDestination)
            : undefined
    const pluginId = numericId && !isNaN(numericId) ? numericId : null
    const batchExportDestination = pluginId ? null : pluginIdOrBatchExportDestination ?? null

    return {
        stage: PIPELINE_TAB_TO_NODE_STAGE[stage + 's'] || null, // pipeline tab has stage plural here we have singular
        pluginId: pluginId,
        batchExportDestination: batchExportDestination,
    }
}

export const scene: SceneExport = {
    component: PipelineNodeNew,
    logic: pipelineNodeNewLogic,
    paramsToProps,
}

interface PluginEntry {
    id: number
    name: string
    description: string | undefined
    plugin: PluginType
    service: null
}
interface BatchExportEntry {
    id: BatchExportService['type']
    name: string
    description: string | undefined
    plugin: null
    service: BatchExportService['type']
}

type TableEntry = PluginEntry | BatchExportEntry

function convertPluginToTableEntry(plugin: PluginType): TableEntry {
    return {
        id: plugin.id,
        name: plugin.name,
        description: plugin.description,
        plugin: plugin,
        service: null,
    }
}

function convertBatchExportToTableEntry(service: BatchExportService['type']): TableEntry {
    return {
        id: service,
        name: service,
        description: `${service} batch export`,
        plugin: null,
        service: service,
    }
}

export function PipelineNodeNew(
    params: { stage?: string; pluginIdOrBatchExportDestination?: string } = {}
): JSX.Element {
    const { stage, pluginId, batchExportDestination } = paramsToProps({ params })
    const { batchExportServiceNames } = useValues(pipelineNodeNewLogic)

    if (!stage) {
        return <NotFound object="pipeline app stage" />
    }

    if (pluginId) {
        return <PipelinePluginConfiguration stage={stage} pluginId={pluginId} />
    }
    if (batchExportDestination) {
        if (stage !== PipelineStage.Destination) {
            return <NotFound object={batchExportDestination} />
        }
        return <PipelineBatchExportConfiguration service={batchExportDestination} />
    }

    if (stage === PipelineStage.Transformation) {
        // Show a list of transformations
        const { plugins, loading } = useValues(pipelineTransformationsLogic)
        const targets = Object.values(plugins).map(convertPluginToTableEntry)
        return nodeOptionsTable(stage, targets, loading)
    } else if (stage === PipelineStage.Destination) {
        const { plugins, loading } = useValues(pipelineDestinationsLogic)
        const pluginTargets = Object.values(plugins).map(convertPluginToTableEntry)
        const batchExportTargets = Object.values(batchExportServiceNames).map(convertBatchExportToTableEntry)
        return nodeOptionsTable(stage, [...batchExportTargets, ...pluginTargets], loading)
    } else if (stage === PipelineStage.SiteApp) {
        const { plugins, loading } = useValues(frontendAppsLogic)
        const targets = Object.values(plugins).map(convertPluginToTableEntry)
        return nodeOptionsTable(stage, targets, loading)
    }
    return <>Creation is unavailable for {stage}</>
}

function nodeOptionsTable(stage: PipelineStage, targets: TableEntry[], loading: boolean): JSX.Element {
    const { createNewButtonPressed } = useActions(pipelineNodeNewLogic)

    return (
        <>
            <LemonTable
                dataSource={targets}
                size="small"
                loading={loading}
                columns={[
                    {
                        title: 'Name',
                        sticky: true,
                        render: function RenderName(_, target) {
                            return (
                                <div className="flex flex-col py-1">
                                    <div className="flex flex-row items-center font-bold text-sm gap-1">
                                        {target.name}
                                    </div>

                                    {target.description ? (
                                        <div className="text-default text-xs text-text-secondary-3000 mt-1">
                                            <LemonMarkdown className="max-w-[30rem]" lowKeyHeadings>
                                                {target.description}
                                            </LemonMarkdown>
                                        </div>
                                    ) : null}
                                </div>
                            )
                        },
                    },
                    {
                        title: 'App',
                        render: function RenderAppInfo(_, target) {
                            if (target.plugin) {
                                return <RenderApp plugin={target.plugin} />
                            }
                            return <RenderBatchExportIcon type={target.service} />
                        },
                    },
                    {
                        title: 'Actions',
                        width: 100,
                        align: 'right',
                        render: function RenderActions(_, target) {
                            return (
                                <LemonButton
                                    type="primary"
                                    data-attr={`new-${stage}-${target.id}`}
                                    onClick={() => createNewButtonPressed(stage, target.id)}
                                    // to={urls.pipelineNodeNew(stage, target.id)}
                                >
                                    Create
                                </LemonButton>
                            )
                        },
                    },
                ]}
            />
        </>
    )
}
