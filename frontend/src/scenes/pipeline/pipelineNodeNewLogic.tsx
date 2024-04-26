import { actions, connect, kea, listeners, path, props, selectors } from 'kea'
import { router } from 'kea-router'
import { capitalizeFirstLetter } from 'lib/utils'
import { Scene } from 'scenes/sceneTypes'
import { urls } from 'scenes/urls'
import { userLogic } from 'scenes/userLogic'

import { BatchExportService, Breadcrumb, PipelineStage, PipelineTab } from '~/types'

import type { pipelineNodeNewLogicType } from './pipelineNodeNewLogicType'

export const NODE_STAGE_TO_PIPELINE_TAB: Partial<Record<PipelineStage, PipelineTab>> = {
    [PipelineStage.Transformation]: PipelineTab.Transformations,
    [PipelineStage.Destination]: PipelineTab.Destinations,
    [PipelineStage.SiteApp]: PipelineTab.SiteApps,
}
export interface PipelineNodeNewLogicProps {
    /** Might be null if a non-existent stage is set in the URL. */
    stage: PipelineStage | null
    pluginId: number | null
    batchExportDestination: string | null
}

export const pipelineNodeNewLogic = kea<pipelineNodeNewLogicType>([
    props({} as PipelineNodeNewLogicProps),
    connect({
        values: [userLogic, ['user']],
    }),
    path((pluginIdOrBatchExportDestination) => [
        'scenes',
        'pipeline',
        'pipelineNodeNewLogic',
        pluginIdOrBatchExportDestination,
    ]),
    actions({
        createNewButtonPressed: (stage: PipelineStage, id: number | BatchExportService['type']) => ({ stage, id }),
    }),
    selectors(() => ({
        breadcrumbs: [
            (_, p) => [p.stage, p.pluginId, p.batchExportDestination],
            (stage, pluginId, batchDestination): Breadcrumb[] => [
                {
                    key: Scene.Pipeline,
                    name: 'Data pipeline',
                    path: urls.pipeline(),
                },
                {
                    key: stage || 'unknown',
                    name: stage ? capitalizeFirstLetter(NODE_STAGE_TO_PIPELINE_TAB[stage] || '') : 'Unknown',
                    path: urls.pipeline(stage ? NODE_STAGE_TO_PIPELINE_TAB[stage] : undefined),
                },
                {
                    key: pluginId || batchDestination || 'Unknown',
                    name: pluginId ? 'New' : batchDestination ? `New ${batchDestination} destination` : 'Options',
                },
            ],
        ],
        batchExportServiceNames: [
            (s) => [s.user],
            (user): BatchExportService['type'][] => {
                const services: BatchExportService['type'][] = ['BigQuery', 'Postgres', 'Redshift', 'Snowflake', 'S3']
                if (user?.is_impersonated) {
                    services.push('HTTP')
                }
                return services
            },
        ],
    })),
    listeners(() => ({
        createNewButtonPressed: ({ stage, id }) => {
            // TODO: this doesn't work either - a refresh is fine
            // error: Rendered fewer hooks than expected. This may be caused by an accidental early return statement.
            router.actions.replace(urls.pipelineNodeNew(stage, id))
            // urls.pipelineNodeNew(stage, target.id)
        },
    })),
])
