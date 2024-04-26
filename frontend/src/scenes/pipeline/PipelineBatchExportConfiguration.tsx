import { useActions, useValues } from 'kea'
import { Form } from 'kea-forms'
import { NotFound } from 'lib/components/NotFound'
import { LemonButton } from 'lib/lemon-ui/LemonButton'
import { LemonCheckbox } from 'lib/lemon-ui/LemonCheckbox'
import { LemonField } from 'lib/lemon-ui/LemonField'
import { LemonInput } from 'lib/lemon-ui/LemonInput'
import { Spinner } from 'lib/lemon-ui/Spinner'
import { BatchExportsEditFields } from 'scenes/batch_exports/BatchExportEditForm'
import { BatchExportConfigurationForm } from 'scenes/batch_exports/batchExportEditLogic'

import { BatchExportService, BatchExportServiceNames } from '~/types'

import { pipelineBatchExportConfigurationLogic } from './pipelineBatchExportConfigurationLogic'

export function PipelineBatchExportConfiguration({ service, id }: { service?: string; id?: string }): JSX.Element {
    if (service && !BatchExportServiceNames.includes(service)) {
        return <NotFound object={`batch export service ${service}`} />
    }

    const logicProps = { service: (service as BatchExportService['type']) || null, id: id || null }
    const logic = pipelineBatchExportConfigurationLogic(logicProps)

    const { isNew, configuration, savedConfiguration, isConfigurationSubmitting, batchExportConfigLoading } =
        useValues(logic)
    const { resetConfiguration, submitConfiguration } = useActions(logic)

    if (batchExportConfigLoading) {
        return <Spinner />
    }

    return (
        <div className="space-y-3">
            <>
                <Form
                    logic={pipelineBatchExportConfigurationLogic}
                    props={logicProps}
                    formKey="configuration"
                    className="space-y-3"
                >
                    <LemonField
                        name="name"
                        label="Name"
                        info="Customising the name can be useful if multiple instances of the same type are used."
                    >
                        <LemonInput type="text" />
                    </LemonField>
                    <LemonField
                        name="description"
                        label="Description"
                        info="Add a description to share context with other team members"
                    >
                        <LemonInput type="text" />
                    </LemonField>
                    <LemonField name="enabled" info="Start continuously exporting from now">
                        {({ value, onChange }) => (
                            <LemonCheckbox label="Enabled" onChange={() => onChange(!value)} checked={value} />
                        )}
                    </LemonField>
                    <BatchExportConfigurationFields isNew={isNew} formValues={configuration} />
                    <div className="flex gap-2">
                        <LemonButton
                            type="secondary"
                            htmlType="reset"
                            onClick={() => resetConfiguration(savedConfiguration || {})}
                            disabledReason={isConfigurationSubmitting ? 'Saving in progress…' : undefined}
                        >
                            {isNew ? 'Reset' : 'Cancel'}
                        </LemonButton>
                        <LemonButton
                            type="primary"
                            htmlType="submit"
                            onClick={submitConfiguration}
                            loading={isConfigurationSubmitting}
                        >
                            {isNew ? 'Create' : 'Save'}
                        </LemonButton>
                    </div>
                </Form>
            </>
        </div>
    )
}

function BatchExportConfigurationFields({
    isNew,
    formValues,
}: {
    isNew: boolean
    formValues: Record<string, any>
}): JSX.Element {
    return (
        <BatchExportsEditFields
            isNew={isNew}
            isPipeline
            batchExportConfigForm={formValues as BatchExportConfigurationForm}
        />
    )
}
